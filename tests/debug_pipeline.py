import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.generator import generate_synthetic_batch
from backend.evidence import EvidenceEngine
from backend.agent import SentinelAPAgent
from backend.metrics import compute_batch_scorecard

def debug_pipeline():
    invoices, pos, vendors, bank_changes = generate_synthetic_batch(seed=42, total_invoices=75)
    engine = EvidenceEngine(pos, vendors, bank_changes)
    dossiers = {inv.invoice_id: engine.build_dossier(inv, invoices) for inv in invoices}
    agent = SentinelAPAgent()
    verdicts = agent.evaluate_batch(invoices, dossiers)
    
    verdict_map = {v.invoice_id: v for v in verdicts}
    print("Mismatches:")
    for inv in invoices:
        v = verdict_map[inv.invoice_id]
        if (v.verdict == "escalate_fraud" and inv.ground_truth_label != "fraud_risk") or (v.verdict != "escalate_fraud" and inv.ground_truth_label == "fraud_risk"):
            print(f"Invoice {inv.invoice_id} ({inv.vendor_name}): Predicted={v.verdict} | True={inv.ground_truth_label} | Reason={v.primary_reason}")

if __name__ == "__main__":
    debug_pipeline()
