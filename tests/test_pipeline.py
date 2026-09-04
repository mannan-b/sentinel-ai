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

def test_synthetic_data_generation_extended():
    invoices, pos, grns, vendors, bank_changes = generate_synthetic_batch(seed=42, total_invoices=75)
    assert len(invoices) == 75
    assert len(vendors) >= 10
    assert len(pos) >= 50
    assert len(grns) >= 40
    assert len(bank_changes) >= 1

    # Verify line items and payment fields exist
    for inv in invoices:
        assert len(inv.line_items) > 0
        assert inv.due_date is not None
        assert inv.payment_terms in ["NET15", "NET30", "NET60", "IMMEDIATE"]

    labels = {inv.ground_truth_label for inv in invoices}
    assert "legitimate" in labels
    assert "duplicate" in labels
    assert "fraud_risk" in labels
    assert "needs_review" in labels

def test_three_way_reconciliation():
    invoices, pos, grns, vendors, bank_changes = generate_synthetic_batch(seed=42, total_invoices=75)
    engine = EvidenceEngine(pos, grns, vendors, bank_changes)
    
    # 1. Test Quantity Mismatch invoice
    qty_inv = next(i for i in invoices if i.invoice_id == "INV-GOS-QTY-OVERBILL")
    rcpt_ev = engine.extract_receipt_evidence(qty_inv)
    assert rcpt_ev.match_status in ["QUANTITY_OVERBILLED", "PARTIAL_RECEIPT_OVERBILL"]
    assert rcpt_ev.invoice_qty_total == 100.0
    assert rcpt_ev.received_qty_total == 60.0

    # 2. Test Price Mismatch invoice
    price_inv = next(i for i in invoices if i.invoice_id == "INV-DATA-PRICE-OVER")
    price_ev = engine.extract_receipt_evidence(price_inv)
    assert price_ev.match_status == "PRICE_MISMATCH"
    assert price_ev.price_discrepancy == 1000.0

    # 3. Test Missing GRN invoice
    missing_grn_inv = next(i for i in invoices if i.invoice_id == "INV-METRO-MISSING-GRN")
    mgrn_ev = engine.extract_receipt_evidence(missing_grn_inv)
    assert mgrn_ev.match_status == "MISSING_GRN"
    assert mgrn_ev.grn_found is False

    # 4. Test Extra Line Item invoice
    extra_inv = next(i for i in invoices if i.invoice_id == "INV-PINN-EXTRA-LINE")
    extra_ev = engine.extract_receipt_evidence(extra_inv)
    assert extra_ev.match_status == "EXTRA_LINE_ITEM"
    assert len(extra_ev.line_item_discrepancies) > 0

def test_hybrid_duplicate_detection():
    # Test string similarity primitives
    assert levenshtein_similarity("INV-2026-001", "INV-2026-001") == 1.0
    assert levenshtein_similarity("INV-2026-001", "INV-2026-001-DUP") > 0.70
    assert token_jaccard_similarity("Monthly server compute", "Monthly server compute cluster") > 0.60

    invoices, pos, grns, vendors, bank_changes = generate_synthetic_batch(seed=42, total_invoices=75)
    engine = EvidenceEngine(pos, grns, vendors, bank_changes)

    dup_inv = next(i for i in invoices if i.invoice_id == "INV-CS-4401-DUP")
    dup_ev = engine.extract_duplicate_evidence(dup_inv, invoices)
    assert dup_ev.is_duplicate_risk is True
    assert dup_ev.exact_duplicate_found is True
    assert len(dup_ev.candidates) > 0
    assert dup_ev.candidates[0].matched_invoice_id == "INV-CS-4401"

def test_controller_exceptions_and_cash_forecasting():
    invoices, pos, grns, vendors, bank_changes = generate_synthetic_batch(seed=42, total_invoices=75)
    engine = EvidenceEngine(pos, grns, vendors, bank_changes)
    dossiers = {inv.invoice_id: engine.build_dossier(inv, invoices) for inv in invoices}
    
    controller = FinanceOperationsController()
    exceptions = controller.generate_exceptions(invoices, dossiers)
    assert len(exceptions) > 0

    # Verify exception prioritization
    assert exceptions[0].priority_score >= exceptions[-1].priority_score

    # Verify exception groups
    groups = controller.group_exceptions(exceptions)
    assert len(groups) > 0

    # Verify bank change alerts
    alerts = controller.generate_bank_change_alerts(invoices, vendors, bank_changes)
    assert len(alerts) >= 1
    assert alerts[0].risk_severity == "CRITICAL"

    # Verify payment queue and cash position
    cash_pos = controller.update_payment_queue_and_cash_position(invoices, dossiers, alerts)
    assert cash_pos.total_approved_payable > 0.0
    assert cash_pos.cash_at_risk > 0.0
    assert len(cash_pos.outflow_forecast) == 4

def test_scorecard_and_agent_verdicts():
    invoices, pos, grns, vendors, bank_changes = generate_synthetic_batch(seed=42, total_invoices=75)
    engine = EvidenceEngine(pos, grns, vendors, bank_changes)
    dossiers = {inv.invoice_id: engine.build_dossier(inv, invoices) for inv in invoices}
    
    agent = SentinelAPAgent()
    verdicts = agent.evaluate_batch(invoices, dossiers)
    assert len(verdicts) == 75

    controller = FinanceOperationsController()
    exceptions = controller.generate_exceptions(invoices, dossiers)
    scorecard = compute_batch_scorecard(invoices, verdicts, dossiers, exceptions)

    assert scorecard.structuring_flagship.detected is True
    assert scorecard.duplicate_metrics.precision == 1.0
    assert scorecard.fraud_metrics.precision == 1.0
    assert scorecard.reconciliation_match_rate > 70.0
    assert scorecard.cash_currently_at_risk > 0.0
    print("\n--- Upgraded AI Finance Controller Scorecard ---")
    print(f"Total Processed: {scorecard.total_invoices}")
    print(f"Reconciliation Match Rate: {scorecard.reconciliation_match_rate}%")
    print(f"Auto-Approved: {scorecard.auto_approved_count} ({scorecard.auto_approved_pct}%)")
    print(f"Exceptions Generated: {scorecard.total_exceptions_count}")
    print(f"Duplicates Rejected: {scorecard.reject_duplicate_count} (${scorecard.duplicate_value_prevented:,.2f} saved)")
    print(f"Fraud Escalated: {scorecard.escalate_fraud_count} (${scorecard.fraud_risk_value_escalated:,.2f})")
    print(f"Cash Currently at Risk: ${scorecard.cash_currently_at_risk:,.2f}")
    print(f"Structuring Flagship: {scorecard.structuring_flagship.headline}")

if __name__ == "__main__":
    test_synthetic_data_generation_extended()
    test_three_way_reconciliation()
    test_hybrid_duplicate_detection()
    test_controller_exceptions_and_cash_forecasting()
    test_scorecard_and_agent_verdicts()
    print("All upgraded test suites passed cleanly!")
