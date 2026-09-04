"""
CLI tool to inspect synthetic AP datasets and run AI Finance Controller evaluations.
"""
import sys
import argparse
from backend.generator import generate_synthetic_batch
from backend.evidence import EvidenceEngine
from backend.agent import SentinelAPAgent
from backend.controller import FinanceOperationsController
from backend.metrics import compute_batch_scorecard
from backend.models import FinanceControlPolicy

def main():
    parser = argparse.ArgumentParser(description="Sentinel AI Finance Controller CLI")
    parser.add_argument("--seed", type=int, default=42, help="Seed for reproducibility")
    parser.add_argument("--size", type=int, default=75, help="Batch size (50-100)")
    args = parser.parse_args()

    print(f"\n[+] Ingesting synthetic AP finance batch (seed={args.seed}, size={args.size})...")
    invoices, pos, grns, vendors, bank_changes = generate_synthetic_batch(seed=args.seed, total_invoices=args.size)
    
    print(f"Ingested {len(invoices)} invoices across {len(vendors)} vendors with {len(pos)} POs and {len(grns)} Goods Receipts (GRNs).")
    
    policy = FinanceControlPolicy()
    engine = EvidenceEngine(pos, grns, vendors, bank_changes, policy=policy)
    dossiers = {inv.invoice_id: engine.build_dossier(inv, invoices) for inv in invoices}
    
    agent = SentinelAPAgent(policy=policy)
    verdicts = agent.evaluate_batch(invoices, dossiers)

    controller = FinanceOperationsController(policy=policy)
    exceptions = controller.generate_exceptions(invoices, dossiers)
    groups = controller.group_exceptions(exceptions)
    alerts = controller.generate_bank_change_alerts(invoices, vendors, bank_changes)
    cash_pos = controller.update_payment_queue_and_cash_position(invoices, dossiers, alerts)
    scorecard = compute_batch_scorecard(invoices, verdicts, dossiers, exceptions)

    print("\n" + "=" * 65)
    print("           SENTINEL AI FINANCE CONTROLLER SCORECARD")
    print("=" * 65)
    print(f"Total Invoices Processed:       {scorecard.total_invoices}")
    print(f"3-Way Reconciliation Match Rate: {scorecard.reconciliation_match_rate}%")
    print(f"Auto-Approved for Payment:      {scorecard.auto_approved_count} ({scorecard.auto_approved_pct}%)")
    print(f"Exceptions Generated:           {scorecard.total_exceptions_count} ({scorecard.exception_rate}%)")
    print(f"Exception Groups (Bulk Issues): {len(groups)}")
    print(f"Duplicates Rejected:            {scorecard.reject_duplicate_count} (${scorecard.duplicate_value_prevented:,.2f} duplicate disbursement prevented)")
    print(f"Fraud / BEC Escalations:        {scorecard.escalate_fraud_count} (${scorecard.fraud_risk_value_escalated:,.2f} fraud exposure halted)")
    print(f"Held for Human Review:          {scorecard.held_for_review_count} (${scorecard.payment_value_blocked:,.2f} blocked in review)")
    print(f"Cash Currently at Risk:         ${scorecard.cash_currently_at_risk:,.2f}")
    print(f"Average Evidence Citations:     {scorecard.avg_evidence_citations_per_non_approval} facts / decision")
    
    print("\n[PROJECTED AP CASH OUTFLOW FORECAST]")
    for b in cash_pos.outflow_forecast:
        print(f"  • {b.days_range:12s}: Approved: ${b.approved_amount:10,.2f} | Held: ${b.held_amount:10,.2f} | High-Risk: ${b.high_risk_amount:10,.2f} | Total: ${b.total_projected_outflow:10,.2f}")

    print("\n[FLAGSHIP FINDING]")
    print(f"Headline: {scorecard.structuring_flagship.headline}")
    print(f"Details:  {scorecard.structuring_flagship.explanation}")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    main()
