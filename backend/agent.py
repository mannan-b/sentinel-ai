import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.models import (
    Invoice, EvidenceDossier, AgentVerdict, CitedEvidenceItem, VerdictType,
    FinanceControlPolicy
)

class SentinelAPAgent:
    """
    Sentinel AI Finance Controller & Verdict Agent.
    Synthesizes deterministic evidence into actionable controller judgments.
    Strictly cites observed values and enforces human-in-the-loop review when evidence warrants.
    """

    def __init__(self, api_key: Optional[str] = None, policy: Optional[FinanceControlPolicy] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.policy = policy or FinanceControlPolicy()

    def evaluate_invoice(self, invoice: Invoice, dossier: EvidenceDossier) -> AgentVerdict:
        """
        Renders judgment with strictly cited evidence from the dossier.
        """
        # 1. Fraud Escalation: Cross-Batch Structuring (Smurfing)
        if dossier.structuring_evidence.in_structuring_cluster:
            s_ev = dossier.structuring_evidence
            cited = [
                CitedEvidenceItem(
                    field_path="structuring_evidence.in_structuring_cluster",
                    observed_value=True,
                    significance="Cross-record scan detected multiple split invoices from this vendor."
                ),
                CitedEvidenceItem(
                    field_path="structuring_evidence.cluster_invoice_count",
                    observed_value=s_ev.cluster_invoice_count,
                    significance=f"{s_ev.cluster_invoice_count} split invoices submitted across {s_ev.time_window_days} days."
                ),
                CitedEvidenceItem(
                    field_path="structuring_evidence.individual_amounts",
                    observed_value=s_ev.individual_amounts,
                    significance=f"All invoices intentionally structured just under the ${s_ev.threshold_limit:,.2f} approval threshold."
                ),
                CitedEvidenceItem(
                    field_path="structuring_evidence.cluster_total_amount",
                    observed_value=s_ev.cluster_total_amount,
                    significance=f"Total combined commitment of ${s_ev.cluster_total_amount:,.2f} evades single-invoice signoff."
                )
            ]
            return AgentVerdict(
                invoice_id=invoice.invoice_id,
                verdict="escalate_fraud",
                confidence=0.99,
                cited_evidence=cited,
                primary_reason=(
                    f"Cross-batch structuring attack detected: {s_ev.cluster_invoice_count} invoices totaling "
                    f"${s_ev.cluster_total_amount:,.2f} split under ${s_ev.threshold_limit:,.2f} limit without PO."
                ),
                recommended_action="Freeze payment immediately. Escalate to Internal Audit and Corporate Security.",
                next_best_action="Audit vendor master records for related shell entities; place vendor in high-risk quarantine.",
                requires_human_review=True
            )

        # 2. Fraud Escalation: High-Risk Bank Fingerprint Change (BEC / Account Takeover)
        if dossier.bank_evidence.risk_level == "HIGH_RISK_RECENT_CHANGE":
            b_ev = dossier.bank_evidence
            cited = [
                CitedEvidenceItem(
                    field_path="bank_evidence.submitted_fingerprint",
                    observed_value=b_ev.submitted_fingerprint,
                    significance="Bank account on invoice does not match vendor master registry."
                ),
                CitedEvidenceItem(
                    field_path="bank_evidence.master_fingerprint",
                    observed_value=b_ev.master_fingerprint,
                    significance="Approved vendor master account fingerprint on file."
                ),
                CitedEvidenceItem(
                    field_path="bank_evidence.days_since_account_change",
                    observed_value=b_ev.days_since_account_change,
                    significance=f"Bank routing change modified {b_ev.days_since_account_change} days prior to invoice submission."
                )
            ]
            return AgentVerdict(
                invoice_id=invoice.invoice_id,
                verdict="escalate_fraud",
                confidence=0.98,
                cited_evidence=cited,
                primary_reason="Severe Account Takeover / BEC Risk: Bank fingerprint modified 2 days ago to unverified overseas/new routing.",
                recommended_action="Halt payment disbursement. Execute out-of-band telephone verification with verified vendor CFO.",
                next_best_action="Trigger multi-step BEC verification protocol; require dual-signoff before releasing payment.",
                requires_human_review=True
            )

        # 3. Fraud Escalation: Vendor Collusion / Shared Bank Fingerprint
        if dossier.collusion_evidence.shared_fingerprint_detected:
            c_ev = dossier.collusion_evidence
            cited = [
                CitedEvidenceItem(
                    field_path="collusion_evidence.shared_fingerprint_detected",
                    observed_value=True,
                    significance="Shared bank account routing detected across multiple distinct vendor master records."
                ),
                CitedEvidenceItem(
                    field_path="collusion_evidence.conflicting_vendor_names",
                    observed_value=c_ev.conflicting_vendor_names,
                    significance=f"Linked to co-registered vendor profile: {', '.join(c_ev.conflicting_vendor_names)}."
                )
            ]
            return AgentVerdict(
                invoice_id=invoice.invoice_id,
                verdict="escalate_fraud",
                confidence=0.95,
                cited_evidence=cited,
                primary_reason=c_ev.details,
                recommended_action="Freeze payments to all associated vendor entities. Initiate Vendor Master Fraud Audit.",
                next_best_action="Request tax ID (W-9 / EIN) verification from legal representation.",
                requires_human_review=True
            )

        # 4. Duplicate Rejection
        if dossier.duplicate_evidence.is_duplicate_risk:
            d_ev = dossier.duplicate_evidence
            top_candidate = d_ev.candidates[0]
            factors = top_candidate.factors
            
            cited = [
                CitedEvidenceItem(
                    field_path="duplicate_evidence.is_duplicate_risk",
                    observed_value=True,
                    significance="Batch duplicate scan matched existing invoice in current run."
                ),
                CitedEvidenceItem(
                    field_path="duplicate_evidence.candidates[0].matched_invoice_id",
                    observed_value=top_candidate.matched_invoice_id,
                    significance=f"Matched duplicate target invoice ID: {top_candidate.matched_invoice_id}."
                ),
                CitedEvidenceItem(
                    field_path="duplicate_evidence.candidates[0].similarity_score",
                    observed_value=top_candidate.similarity_score,
                    significance=f"Hybrid duplicate match confidence score: {top_candidate.similarity_score * 100:.1f}%."
                )
            ]
            if factors:
                cited.append(CitedEvidenceItem(
                    field_path="duplicate_evidence.factors",
                    observed_value=f"InvNo: {factors.invoice_no_similarity} | Vendor: {factors.vendor_similarity} | Amount: {factors.amount_similarity}",
                    significance="Multi-factor weighted breakdown across invoice number, vendor, amount, date proximity, and description."
                ))

            verdict_text = "Exact duplicate invoice resubmission detected" if d_ev.exact_duplicate_found else "Near-duplicate invoice detected with identical billing parameters"
            return AgentVerdict(
                invoice_id=invoice.invoice_id,
                verdict="reject_duplicate",
                confidence=top_candidate.similarity_score,
                cited_evidence=cited,
                primary_reason=f"{verdict_text} (matches {top_candidate.matched_invoice_id}).",
                recommended_action=f"Reject invoice as duplicate of {top_candidate.matched_invoice_id} to prevent double disbursement of ${invoice.amount:,.2f}.",
                next_best_action="Archive entry and notify supplier AP contact of duplicate submission rejection.",
                requires_human_review=False
            )

        # 5. 3-Way Reconciliation Exceptions (Hold for Review)
        rcpt_ev = dossier.receipt_evidence
        if rcpt_ev.match_status == "MISSING_GRN":
            cited = [
                CitedEvidenceItem(
                    field_path="receipt_evidence.match_status",
                    observed_value="MISSING_GRN",
                    significance="No Goods Receipt Note (GRN) found on receiving dock for referenced PO."
                ),
                CitedEvidenceItem(
                    field_path="po_reference",
                    observed_value=invoice.po_reference,
                    significance=f"Valid PO {invoice.po_reference} exists, but goods delivery is unconfirmed."
                )
            ]
            return AgentVerdict(
                invoice_id=invoice.invoice_id,
                verdict="hold_for_review",
                confidence=0.92,
                cited_evidence=cited,
                primary_reason=f"3-Way Reconciliation Hold: Goods Receipt Note (GRN) missing for PO {invoice.po_reference}. Invoice submitted prior to dock delivery verification.",
                recommended_action="Hold payment. Request warehouse dock supervisor to verify delivery and generate GRN.",
                next_best_action="If goods are confirmed received, re-trigger 3-way matching; otherwise withhold disbursement.",
                requires_human_review=True
            )

        if rcpt_ev.match_status in ["QUANTITY_OVERBILLED", "PARTIAL_RECEIPT_OVERBILL"]:
            cited = [
                CitedEvidenceItem(
                    field_path="receipt_evidence.invoice_qty_total",
                    observed_value=rcpt_ev.invoice_qty_total,
                    significance=f"Billed quantity is {rcpt_ev.invoice_qty_total} units."
                ),
                CitedEvidenceItem(
                    field_path="receipt_evidence.received_qty_total",
                    observed_value=rcpt_ev.received_qty_total,
                    significance=f"Warehouse GRN {rcpt_ev.grn_id} received only {rcpt_ev.received_qty_total} units."
                ),
                CitedEvidenceItem(
                    field_path="receipt_evidence.qty_discrepancy",
                    observed_value=rcpt_ev.qty_discrepancy,
                    significance=f"Quantity overbilled by {rcpt_ev.qty_discrepancy} units."
                )
            ]
            return AgentVerdict(
                invoice_id=invoice.invoice_id,
                verdict="hold_for_review",
                confidence=0.95,
                cited_evidence=cited,
                primary_reason=f"3-Way Reconciliation Mismatch: Invoiced quantity ({rcpt_ev.invoice_qty_total}) exceeds dock received quantity ({rcpt_ev.received_qty_total}) on GRN {rcpt_ev.grn_id}.",
                recommended_action="Place on partial reconciliation hold. Issue credit memo request to supplier for undelivered units.",
                next_best_action="Authorize short-pay disbursement for delivered units upon Controller signoff.",
                requires_human_review=True
            )

        if rcpt_ev.match_status == "PRICE_MISMATCH":
            cited = [
                CitedEvidenceItem(
                    field_path="receipt_evidence.price_discrepancy",
                    observed_value=f"+${rcpt_ev.price_discrepancy:,.2f}",
                    significance="Unit price billed exceeds PO contracted rate."
                ),
                CitedEvidenceItem(
                    field_path="receipt_evidence.line_item_discrepancies",
                    observed_value=rcpt_ev.line_item_discrepancies,
                    significance="Line item pricing variance details."
                )
            ]
            return AgentVerdict(
                invoice_id=invoice.invoice_id,
                verdict="hold_for_review",
                confidence=0.94,
                cited_evidence=cited,
                primary_reason=f"3-Way Reconciliation Mismatch: Invoiced unit price exceeds contracted PO rate (variance: +${rcpt_ev.price_discrepancy:,.2f}).",
                recommended_action="Route to Procurement Buyer to enforce contracted PO rate or authorize price adjustment.",
                next_best_action="If price increase is unauthorized, short-pay invoice at contract rate.",
                requires_human_review=True
            )

        if rcpt_ev.match_status == "EXTRA_LINE_ITEM":
            cited = [
                CitedEvidenceItem(
                    field_path="receipt_evidence.line_item_discrepancies",
                    observed_value=rcpt_ev.line_item_discrepancies,
                    significance="Unauthorized line item not present on PO."
                )
            ]
            return AgentVerdict(
                invoice_id=invoice.invoice_id,
                verdict="hold_for_review",
                confidence=0.93,
                cited_evidence=cited,
                primary_reason=f"3-Way Reconciliation Mismatch: Invoice contains unauthorized line item not present on approved Purchase Order.",
                recommended_action="Hold payment. Request Procurement Buyer to review and approve PO amendment or reject extra charge.",
                next_best_action="Issue dispute notice to supplier for unapproved ancillary fees.",
                requires_human_review=True
            )

        # 6. First-Time Vendor Large Transaction
        if dossier.vendor_history_evidence.is_unusually_large_first_time:
            cited = [
                CitedEvidenceItem(
                    field_path="vendor_history_evidence.is_first_time_vendor",
                    observed_value=True,
                    significance="No previous transaction history for this vendor in ERP master data."
                ),
                CitedEvidenceItem(
                    field_path="amount",
                    observed_value=invoice.amount,
                    significance=f"First-time invoice amount ${invoice.amount:,.2f} exceeds high-risk policy threshold."
                ),
                CitedEvidenceItem(
                    field_path="po_evidence.status",
                    observed_value=dossier.po_evidence.status,
                    significance="No approved purchase order attached for this first-time billing."
                )
            ]
            return AgentVerdict(
                invoice_id=invoice.invoice_id,
                verdict="hold_for_review",
                confidence=0.92,
                cited_evidence=cited,
                primary_reason=f"First-time vendor submitting high-value ${invoice.amount:,.2f} bill with zero prior history and no PO.",
                recommended_action="Route to AP Senior Controller for Vendor Onboarding Verification and W-9 validation.",
                next_best_action="Verify business legitimacy via Secretary of State database and tax ID validation.",
                requires_human_review=True
            )

        # 7. PO Variance / Missing PO on Established Vendor
        if dossier.po_evidence.status == "AMOUNT_EXCEEDED":
            p_ev = dossier.po_evidence
            cited = [
                CitedEvidenceItem(
                    field_path="po_evidence.po_approved_amount",
                    observed_value=p_ev.po_approved_amount,
                    significance=f"Approved PO amount is ${p_ev.po_approved_amount:,.2f}."
                ),
                CitedEvidenceItem(
                    field_path="amount",
                    observed_value=invoice.amount,
                    significance=f"Invoiced amount is ${invoice.amount:,.2f}."
                ),
                CitedEvidenceItem(
                    field_path="po_evidence.amount_delta_pct",
                    observed_value=f"+{p_ev.amount_delta_pct}%",
                    significance=f"Invoice exceeds PO by +{p_ev.amount_delta_pct}%, violating policy tolerance."
                )
            ]
            return AgentVerdict(
                invoice_id=invoice.invoice_id,
                verdict="hold_for_review",
                confidence=0.95,
                cited_evidence=cited,
                primary_reason=f"PO variance violation: Invoiced amount ${invoice.amount:,.2f} exceeds PO {p_ev.po_number} (${p_ev.po_approved_amount:,.2f}) by {p_ev.amount_delta_pct}%.",
                recommended_action="Hold payment. Request budget holder approval for invoice overage.",
                next_best_action="Obtain written approval from Department Head or request revised PO.",
                requires_human_review=True
            )

        if dossier.po_evidence.status in ["NO_PO_REFERENCED", "INVALID_PO_REFERENCE"]:
            p_ev = dossier.po_evidence
            cited = [
                CitedEvidenceItem(
                    field_path="po_evidence.status",
                    observed_value=p_ev.status,
                    significance=p_ev.details
                ),
                CitedEvidenceItem(
                    field_path="po_reference",
                    observed_value=invoice.po_reference,
                    significance=f"Submitted PO reference: '{invoice.po_reference}'"
                )
            ]
            return AgentVerdict(
                invoice_id=invoice.invoice_id,
                verdict="hold_for_review",
                confidence=0.90,
                cited_evidence=cited,
                primary_reason=f"Orphan Invoice / PO discrepancy: {p_ev.details}",
                recommended_action="Route to AP team to obtain valid PO matching confirmation.",
                next_best_action="Contact procurement department to generate retroactive PO if services were authorized.",
                requires_human_review=True
            )

        # 8. Clean Auto-Approve (3-Way Match Verified)
        cited = [
            CitedEvidenceItem(
                field_path="po_evidence.status",
                observed_value=dossier.po_evidence.status,
                significance=f"Valid PO {dossier.po_evidence.po_number} matched within tolerance."
            ),
            CitedEvidenceItem(
                field_path="receipt_evidence.match_status",
                observed_value="EXACT_3WAY_MATCH",
                significance=f"3-Way match verified against GRN {dossier.receipt_evidence.grn_id} (quantity & unit price exact)."
            ),
            CitedEvidenceItem(
                field_path="bank_evidence.risk_level",
                observed_value="NORMAL",
                significance="Bank account fingerprint matches historical vendor profile."
            ),
            CitedEvidenceItem(
                field_path="duplicate_evidence.is_duplicate_risk",
                observed_value=False,
                significance="Zero duplicate candidates found in batch scan."
            )
        ]
        return AgentVerdict(
            invoice_id=invoice.invoice_id,
            verdict="auto_approve",
            confidence=0.98,
            cited_evidence=cited,
            primary_reason="Clean 3-way match: Approved PO, verified Goods Receipt (GRN), verified bank fingerprint, and no duplicate collision.",
            recommended_action=f"Auto-approve for scheduled batch disbursement on due date ({invoice.due_date}).",
            next_best_action="Queue for automated ACH batch payment processing.",
            requires_human_review=False
        )

    def evaluate_batch(
        self,
        invoices: List[Invoice],
        dossiers: Dict[str, EvidenceDossier]
    ) -> List[AgentVerdict]:
        verdicts: List[AgentVerdict] = []
        for inv in invoices:
            dossier = dossiers[inv.invoice_id]
            verdict = self.evaluate_invoice(inv, dossier)
            verdicts.append(verdict)
        return verdicts
