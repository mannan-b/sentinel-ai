import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from backend.generator import generate_synthetic_batch
from backend.evidence import EvidenceEngine, levenshtein_similarity, token_jaccard_similarity
from backend.agent import SentinelAPAgent
from backend.controller import FinanceOperationsController
from backend.metrics import compute_batch_scorecard
from backend.models import FinanceControlPolicy
from backend.audit import audit_trail

def test_clean_invoice_reaches_payment_eligible():
    invoices, pos, grns, vendors, bank_changes = generate_synthetic_batch(seed=42, total_invoices=75)
    engine = EvidenceEngine(pos, grns, vendors, bank_changes)
    
    # Pick a clean invoice
    clean_inv = next(i for i in invoices if i.ground_truth_label == "legitimate" and i.po_reference is not None and not i.invoice_id.endswith("-VAR"))
    dossier = engine.build_dossier(clean_inv, invoices)
    
    agent = SentinelAPAgent()
    verdict = agent.evaluate_invoice(clean_inv, dossier)
    assert verdict.verdict == "auto_approve"
    assert verdict.requires_human_review is False
    
    controller = FinanceOperationsController()
    permitted, blocking, satisfied, pending = controller.can_release_payment(
        invoice=clean_inv, dossier=dossier, exceptions=[], bank_alert=None
    )
    assert permitted is True
    assert len(blocking) == 0

def test_missing_grn_blocks_payment():
    invoices, pos, grns, vendors, bank_changes = generate_synthetic_batch(seed=42, total_invoices=75)
    engine = EvidenceEngine(pos, grns, vendors, bank_changes)
    
    missing_grn_inv = next(i for i in invoices if i.invoice_id == "INV-METRO-MISSING-GRN")
    dossier = engine.build_dossier(missing_grn_inv, invoices)
    assert dossier.receipt_evidence.match_status == "MISSING_GRN"
    
    controller = FinanceOperationsController()
    exceptions = controller.generate_exceptions([missing_grn_inv], {missing_grn_inv.invoice_id: dossier})
    assert any(e.exception_type == "MISSING_GRN" for e in exceptions)
    
    permitted, blocking, satisfied, pending = controller.can_release_payment(
        invoice=missing_grn_inv, dossier=dossier, exceptions=exceptions, bank_alert=None
    )
    assert permitted is False
    assert any("Missing Goods Receipt" in b for b in blocking)

def test_resolving_grn_recalculates_payment_and_cash():
    invoices, pos, grns, vendors, bank_changes = generate_synthetic_batch(seed=42, total_invoices=75)
    engine = EvidenceEngine(pos, grns, vendors, bank_changes)
    
    inv = next(i for i in invoices if i.invoice_id == "INV-METRO-MISSING-GRN")
    dossier = engine.build_dossier(inv, invoices)
    controller = FinanceOperationsController()
    exceptions = controller.generate_exceptions([inv], {inv.invoice_id: dossier})
    
    # Calculate initial cash exposure
    initial_cash = controller.update_payment_queue_and_cash_position(invoices, {i.invoice_id: engine.build_dossier(i, invoices) for i in invoices}, [])
    initial_risk = initial_cash.cash_at_risk
    
    # Now simulate attaching/receiving GRN
    from backend.models import GoodsReceipt
    new_grn = GoodsReceipt(
        grn_id="GRN-METRO-9001",
        po_reference=inv.po_reference,
        vendor_id=inv.vendor_id,
        vendor_name=inv.vendor_name,
        received_date=inv.submission_date,
        line_items=inv.line_items,
        receiving_status="FULL"
    )
    grns.append(new_grn)
    
    # Rebuild evidence with updated GRN registry
    engine_updated = EvidenceEngine(pos, grns, vendors, bank_changes)
    updated_dossier = engine_updated.build_dossier(inv, invoices)
    assert updated_dossier.receipt_evidence.match_status == "EXACT_3WAY_MATCH"
    
    # Resolve exception
    ex = exceptions[0]
    ex.status = "RESOLVED"
    
    # Re-check payment release
    permitted, blocking, satisfied, pending = controller.can_release_payment(
        invoice=inv, dossier=updated_dossier, exceptions=exceptions, bank_alert=None
    )
    assert permitted is True

def test_bec_cannot_release_without_required_controls():
    invoices, pos, grns, vendors, bank_changes = generate_synthetic_batch(seed=42, total_invoices=75)
    engine = EvidenceEngine(pos, grns, vendors, bank_changes)
    
    bec_inv = next(i for i in invoices if i.invoice_id == "INV-CYBER-9021")
    dossier = engine.build_dossier(bec_inv, invoices)
    assert dossier.bank_evidence.risk_level == "HIGH_RISK_RECENT_CHANGE"
    
    controller = FinanceOperationsController()
    alerts = controller.generate_bank_change_alerts(invoices, vendors, bank_changes)
    alert = next(a for a in alerts if a.vendor_id == bec_inv.vendor_id)
    
    # Check that payment release fails when controls are pending
    permitted, blocking, satisfied, pending = controller.can_release_payment(
        invoice=bec_inv, dossier=dossier, exceptions=[], bank_alert=alert
    )
    assert permitted is False
    assert len(blocking) >= 3 # Out-of-band phone, CFO signoff, cooling period
    
    # Verify cooling period compliance cannot be bypassed if days < 30
    assert alert.days_since_change == 2
    alert.independent_phone_verified = "VERIFIED"
    alert.cfo_signoff = "VERIFIED"
    alert.account_ownership_verified = "VERIFIED"
    
    # Payment still blocked because cooling period (2 days < 30 days) is not satisfied
    permitted, blocking, satisfied, pending = controller.can_release_payment(
        invoice=bec_inv, dossier=dossier, exceptions=[], bank_alert=alert
    )
    assert permitted is False
    assert any("Cooling Period" in b for b in blocking)

def test_structuring_creates_grouped_exception():
    invoices, pos, grns, vendors, bank_changes = generate_synthetic_batch(seed=42, total_invoices=75)
    engine = EvidenceEngine(pos, grns, vendors, bank_changes)
    dossiers = {inv.invoice_id: engine.build_dossier(inv, invoices) for inv in invoices}
    
    controller = FinanceOperationsController()
    exceptions = controller.generate_exceptions(invoices, dossiers)
    groups = controller.group_exceptions(exceptions)
    
    # Verify Apex Security structuring cluster is consolidated into 1 group
    apex_group = next((g for g in groups if "Apex Security" in g.vendor_name and "STRUCTURING" in g.exception_type), None)
    assert apex_group is not None
    assert apex_group.invoice_count == 4
    assert apex_group.total_financial_impact == 38000.0

def test_duplicate_detection_rejects_true_duplicate():
    invoices, pos, grns, vendors, bank_changes = generate_synthetic_batch(seed=42, total_invoices=75)
    engine = EvidenceEngine(pos, grns, vendors, bank_changes)
    
    dup_inv = next(i for i in invoices if i.invoice_id == "INV-CS-4401-DUP")
    dossier = engine.build_dossier(dup_inv, invoices)
    assert dossier.duplicate_evidence.is_duplicate_risk is True
    
    agent = SentinelAPAgent()
    verdict = agent.evaluate_invoice(dup_inv, dossier)
    assert verdict.verdict == "reject_duplicate"
    assert any(c.field_path == "duplicate_evidence.is_duplicate_risk" for c in verdict.cited_evidence)

def test_distinct_pos_protect_legitimate_recurring_invoice():
    invoices, pos, grns, vendors, bank_changes = generate_synthetic_batch(seed=42, total_invoices=75)
    engine = EvidenceEngine(pos, grns, vendors, bank_changes)
    
    # INV-DATAPULSE-M2 and INV-DATAPULSE-M1 share same amount and vendor but have distinct valid POs
    inv_m2 = next((i for i in invoices if i.invoice_id == "INV-DATAPULSE-M2"), None)
    if inv_m2:
        dossier = engine.build_dossier(inv_m2, invoices)
        assert dossier.duplicate_evidence.is_duplicate_risk is False
        agent = SentinelAPAgent()
        verdict = agent.evaluate_invoice(inv_m2, dossier)
        assert verdict.verdict == "auto_approve"

def test_exception_assignment_updates_owner():
    invoices, pos, grns, vendors, bank_changes = generate_synthetic_batch(seed=42, total_invoices=75)
    engine = EvidenceEngine(pos, grns, vendors, bank_changes)
    dossiers = {inv.invoice_id: engine.build_dossier(inv, invoices) for inv in invoices}
    
    controller = FinanceOperationsController()
    exceptions = controller.generate_exceptions(invoices, dossiers)
    
    # 3-way discrepancy assigned to PROCUREMENT_BUYER
    price_ex = next(e for e in exceptions if e.exception_type == "PRICE_MISMATCH")
    assert price_ex.suggested_owner == "PROCUREMENT_BUYER"
    
    # Structuring assigned to INTERNAL_AUDIT
    struc_ex = next(e for e in exceptions if e.exception_type == "STRUCTURING_ATTACK")
    assert struc_ex.suggested_owner == "INTERNAL_AUDIT"

def test_audit_trail_hash_chain_integrity():
    audit_trail.clear()
    
    # Add a sequence of events
    ev1 = audit_trail.log(action="BATCH_INGESTED", actor="SYSTEM", affected_record="Batch_42", new_state="75 Invoices", reason="Initial ingestion")
    ev2 = audit_trail.log(action="VERDICT_GENERATED", actor="AGENT", affected_record="INV-1001", new_state="AUTO_APPROVE", reason="All 3-way matches clear")
    ev3 = audit_trail.log(action="EXCEPTION_RESOLVED", actor="CONTROLLER", affected_record="EXC-001", new_state="RESOLVED", reason="GRN attached by supervisor")
    
    assert ev1.previous_hash == "0000000000000000000000000000000000000000000000000000000000000000"
    assert ev2.previous_hash == ev1.event_hash
    assert ev3.previous_hash == ev2.event_hash
    
    is_valid, msg = audit_trail.verify_chain_integrity()
    assert is_valid is True
    assert "verified" in msg.lower()
    
    # Tamper with event 2 to verify cryptographic catch
    ev2.reason = "TAMPERED ILLEGAL MUTATION"
    is_valid_tampered, tamper_msg = audit_trail.verify_chain_integrity()
    assert is_valid_tampered is False
    assert "corruption detected" in tamper_msg.lower() or "broken link" in tamper_msg.lower()

def test_stp_rate_comes_from_actual_states():
    invoices, pos, grns, vendors, bank_changes = generate_synthetic_batch(seed=42, total_invoices=75)
    engine = EvidenceEngine(pos, grns, vendors, bank_changes)
    dossiers = {inv.invoice_id: engine.build_dossier(inv, invoices) for inv in invoices}
    
    agent = SentinelAPAgent()
    verdicts = agent.evaluate_batch(invoices, dossiers)
    controller = FinanceOperationsController()
    exceptions = controller.generate_exceptions(invoices, dossiers)
    
    scorecard = compute_batch_scorecard(invoices, verdicts, dossiers, exceptions)
    assert scorecard.stp_count > 0
    assert scorecard.stp_rate == round((scorecard.stp_count / len(invoices)) * 100, 1)
    assert scorecard.stp_rate >= 50.0

def test_ground_truth_is_not_visible_to_agent():
    invoices, pos, grns, vendors, bank_changes = generate_synthetic_batch(seed=42, total_invoices=75)
    engine = EvidenceEngine(pos, grns, vendors, bank_changes)
    
    for inv in invoices:
        dossier = engine.build_dossier(inv, invoices)
        # Verify ground truth label is NEVER present in EvidenceDossier
        dossier_dict = dossier.dict()
        assert "ground_truth_label" not in dossier_dict
        assert "ground_truth_reason" not in dossier_dict

