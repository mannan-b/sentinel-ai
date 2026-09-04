import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from backend.generator import generate_synthetic_batch
from backend.evidence import EvidenceEngine
from backend.agent import SentinelAPAgent
from backend.metrics import compute_batch_scorecard

def test_synthetic_data_generation():
    invoices, pos, vendors, bank_changes = generate_synthetic_batch(seed=42, total_invoices=75)
    assert len(invoices) == 75
    assert len(vendors) >= 10
    assert len(pos) >= 50
    assert len(bank_changes) >= 1
    
    # Check that ground truth labels are present
    labels = {inv.ground_truth_label for inv in invoices}
    assert "legitimate" in labels
    assert "duplicate" in labels
    assert "fraud_risk" in labels
    assert "needs_review" in labels

def test_evidence_and_verdict_pipeline():
    invoices, pos, vendors, bank_changes = generate_synthetic_batch(seed=42, total_invoices=75)
    engine = EvidenceEngine(pos, vendors, bank_changes)
    
    dossiers = {inv.invoice_id: engine.build_dossier(inv, invoices) for inv in invoices}
    assert len(dossiers) == 75
    
    # Verify structuring cluster was extracted
    structuring_dossiers = [d for d in dossiers.values() if d.structuring_evidence.in_structuring_cluster]
    assert len(structuring_dossiers) == 4
    assert structuring_dossiers[0].structuring_evidence.cluster_total_amount == 38000.0
    
    agent = SentinelAPAgent()
    verdicts = agent.evaluate_batch(invoices, dossiers)
    assert len(verdicts) == 75
    
    # Verify non-approval verdicts all have cited evidence
    for v in verdicts:
        if v.verdict != "auto_approve":
            assert len(v.cited_evidence) > 0, f"Invoice {v.invoice_id} with verdict {v.verdict} must have cited evidence"
            assert v.confidence > 0.0
            assert len(v.primary_reason) > 0

    scorecard = compute_batch_scorecard(invoices, verdicts, dossiers)
    assert scorecard.structuring_flagship.detected is True
    assert scorecard.duplicate_metrics.precision == 1.0
    assert scorecard.duplicate_metrics.recall == 1.0
    assert scorecard.fraud_metrics.precision == 1.0
    assert scorecard.fraud_metrics.recall == 1.0
    assert scorecard.legitimate_false_positive_count == 0
    assert scorecard.avg_evidence_citations_per_non_approval >= 2.0
    print("\n--- Pipeline Scorecard Test Passed Successfully ---")
    print(f"Total: {scorecard.total_invoices}")
    print(f"Auto-Approved: {scorecard.auto_approved_count} ({scorecard.auto_approved_pct}%)")
    print(f"Held for Review: {scorecard.held_for_review_count} ({scorecard.held_for_review_pct}%)")
    print(f"Fraud Escalated: {scorecard.escalate_fraud_count} ({scorecard.escalate_fraud_pct}%)")
    print(f"Duplicates Rejected: {scorecard.reject_duplicate_count} ({scorecard.reject_duplicate_pct}%)")
    print(f"Structuring Flagship Caught: {scorecard.structuring_flagship.headline}")

if __name__ == "__main__":
    test_synthetic_data_generation()
    test_evidence_and_verdict_pipeline()
    print("All tests passed!")
