import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.generator import generate_synthetic_batch
from backend.evidence import EvidenceEngine
from backend.agent import SentinelAPAgent

invoices, pos, grns, vendors, bank_changes = generate_synthetic_batch(seed=42, total_invoices=75)
engine = EvidenceEngine(pos, grns, vendors, bank_changes)
dossiers = {inv.invoice_id: engine.build_dossier(inv, invoices) for inv in invoices}
agent = SentinelAPAgent()
verdicts = agent.evaluate_batch(invoices, dossiers)

print("Duplicate Verdicts:")
for inv in invoices:
    v = next(v for v in verdicts if v.invoice_id == inv.invoice_id)
    if v.verdict == "reject_duplicate" or inv.ground_truth_label == "duplicate":
        print(f"ID: {inv.invoice_id} | GT: {inv.ground_truth_label} | Verdict: {v.verdict} | DupScore: {dossiers[inv.invoice_id].duplicate_evidence.duplicate_score} | Reason: {v.primary_reason}")
