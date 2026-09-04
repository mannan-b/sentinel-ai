"""
CLI tool to inspect synthetic AP datasets and run offline batch evaluations.
"""
import sys
import argparse
from tabulate import tabulate
from backend.generator import generate_synthetic_batch
from backend.evidence import EvidenceEngine
from backend.agent import SentinelAPAgent
from backend.metrics import compute_batch_scorecard

def main():
    parser = argparse.ArgumentParser(description="Sentinel AP Synthetic Data Generator & Evaluator")
    parser.add_argument("--seed", type=int, default=42, help="Seed for reproducibility")
    parser.add_argument("--size", type=int, default=75, help="Batch size (50-100)")
    args = parser.parse_args()

    print(f"\n[+] Generating synthetic AP batch (seed={args.seed}, size={args.size})...")
    invoices, pos, vendors, bank_changes = generate_synthetic_batch(seed=args.seed, total_invoices=args.size)
    
    print(f"Generated {len(invoices)} invoices across {len(vendors)} vendors with {len(pos)} purchase orders.")
    
    engine = EvidenceEngine(pos, vendors, bank_changes)
    dossiers = {inv.invoice_id: engine.build_dossier(inv, invoices) for inv in invoices}
    
    agent = SentinelAPAgent()
    verdicts = agent.evaluate_batch(invoices, dossiers)
    scorecard = compute_batch_scorecard(invoices, verdicts, dossiers)

    print("\n" + "=" * 60)
    print("SENTINEL AGENT EVALUATION SCORECARD")
    print("=" * 60)
    print(f"Total Invoices:           {scorecard.total_invoices}")
    print(f"Auto-Approved:            {scorecard.auto_approved_count} ({scorecard.auto_approved_pct}%)")
    print(f"Duplicates Rejected:      {scorecard.reject_duplicate_count} ({scorecard.reject_duplicate_pct}%)")
    print(f"Fraud Risk Escalations:   {scorecard.escalate_fraud_count} ({scorecard.escalate_fraud_pct}%)")
    print(f"Held for Human Review:    {scorecard.held_for_review_count} ({scorecard.held_for_review_pct}%)")
    print(f"Auto-Resolution Rate:     {scorecard.auto_resolved_pct}%")
    print(f"Legitimate False Positives: {scorecard.legitimate_false_positive_count}")
    print(f"Avg Evidence Citations:   {scorecard.avg_evidence_citations_per_non_approval} facts/flag")
    print("\n[FLAGSHIP FINDING]")
    print(f"Headline: {scorecard.structuring_flagship.headline}")
    print(f"Details:  {scorecard.structuring_flagship.explanation}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
