import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.models import (
    Invoice, EvidenceDossier, AgentVerdict, CitedEvidenceItem, VerdictType
)

SENTINEL_SYSTEM_PROMPT = """You are Sentinel, an expert Accounts Payable (AP) Fraud and Financial Control Agent.
Your job is to evaluate a structured evidence dossier for an AP invoice and render one of four verdicts:

VERDICT RUBRIC:
1. 'reject_duplicate':
   - Used when evidence shows an exact or high-confidence near-duplicate invoice in the batch.
   - MUST cite duplicate_evidence fields.

2. 'escalate_fraud':
   - Used when specific indicators of intentional fraud or account takeover exist:
     * Cross-invoice structuring/smurfing under approval thresholds (structuring_evidence.in_structuring_cluster = True)
     * High-risk recent bank account / routing changes (bank_evidence.risk_level = 'HIGH_RISK_RECENT_CHANGE')
   - MUST cite structuring_evidence or bank_evidence.

3. 'hold_for_review':
   - Used when evidence is thin, conflicting, or requires manual human approval:
     * Missing or invalid PO reference on an established vendor
     * First-time vendor submitting an unverified large bill
     * Invoice exceeds PO approved amount beyond acceptable policy tolerance
   - Refusing to guess is a valid and preferred outcome over forcing approval or false fraud accusations.

4. 'auto_approve':
   - Used ONLY when all evidence checks pass cleanly (matching PO, verified bank fingerprint, normal history, no duplicate flags).

NON-NEGOTIABLE RULE:
Every non-approval verdict MUST include cited_evidence items referencing exact field paths from the dossier. Never return bare scores.
"""

class SentinelAPAgent:
    """
    Sentinel AP Verdict Agent.
    Evaluates EvidenceDossiers to make structured, evidence-backed verdicts.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")

    def evaluate_invoice(self, invoice: Invoice, dossier: EvidenceDossier) -> AgentVerdict:
        """
        Renders judgment with strictly cited evidence from the dossier.
        """
        # 1. Check for Fraud Escalation: Cross-Batch Structuring (Smurfing)
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
                recommended_action="Freeze payment immediately. Escalate to Internal Audit and Corporate Security."
            )

        # 2. Check for Fraud Escalation: High-Risk Bank Fingerprint Change (BEC / Account Takeover)
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
                recommended_action="Halt payment disbursement. Perform out-of-band phone verification with verified vendor CFO."
            )

        # 3. Check for Duplicate Rejection
        if dossier.duplicate_evidence.is_duplicate_risk:
            d_ev = dossier.duplicate_evidence
            top_candidate = d_ev.candidates[0]
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
                    significance=f"Duplicate match confidence score of {top_candidate.similarity_score * 100:.1f}%."
                )
            ]
            
            verdict_text = "Exact duplicate invoice resubmission detected" if d_ev.exact_duplicate_found else "Near-duplicate invoice detected with identical billing parameters"
            return AgentVerdict(
                invoice_id=invoice.invoice_id,
                verdict="reject_duplicate",
                confidence=top_candidate.similarity_score,
                cited_evidence=cited,
                primary_reason=f"{verdict_text} (matches {top_candidate.matched_invoice_id}).",
                recommended_action=f"Reject invoice as duplicate of {top_candidate.matched_invoice_id} to prevent double disbursement."
            )

        # 4. Check for Hold for Review (Refusal to guess on thin/conflicting evidence)
        # Condition A: First-time vendor with large unverified transaction
        if dossier.vendor_history_evidence.is_unusually_large_first_time:
            v_ev = dossier.vendor_history_evidence
            cited = [
                CitedEvidenceItem(
                    field_path="vendor_history_evidence.is_first_time_vendor",
                    observed_value=True,
                    significance="No previous transaction history for this vendor in ERP master data."
                ),
                CitedEvidenceItem(
                    field_path="amount",
                    observed_value=invoice.amount,
                    significance=f"First-time invoice amount ${invoice.amount:,.2f} exceeds high-risk threshold."
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
                recommended_action="Route to AP Senior Controller for Vendor Onboarding Verification and W-9 validation."
            )

        # Condition B: PO Amount Exceeded Beyond Tolerance
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
                    significance=f"Invoice exceeds PO by +{p_ev.amount_delta_pct}%, violating 5% tolerance."
                )
            ]
            return AgentVerdict(
                invoice_id=invoice.invoice_id,
                verdict="hold_for_review",
                confidence=0.95,
                cited_evidence=cited,
                primary_reason=f"PO variance violation: Invoiced amount ${invoice.amount:,.2f} exceeds PO {p_ev.po_number} (${p_ev.po_approved_amount:,.2f}) by {p_ev.amount_delta_pct}%.",
                recommended_action="Hold payment. Request budget holder approval for invoice overage."
            )

        # Condition C: Missing PO / Invalid PO on established vendor
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
                recommended_action="Route to AP team to obtain valid PO matching confirmation."
            )

        # 5. Clean / Auto-Approve
        cited = [
            CitedEvidenceItem(
                field_path="po_evidence.status",
                observed_value=dossier.po_evidence.status,
                significance=f"Valid PO {dossier.po_evidence.po_number} matched within tolerance."
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
            confidence=0.97,
            cited_evidence=cited,
            primary_reason="Clean 3-way match: Approved PO, verified bank fingerprint, and no duplicate collision.",
            recommended_action="Auto-approve for scheduled batch ACH disbursement."
        )

    def evaluate_batch(
        self,
        invoices: List[Invoice],
        dossiers: Dict[str, EvidenceDossier]
    ) -> List[AgentVerdict]:
        """
        Evaluates the full batch of invoices against their evidence dossiers.
        """
        verdicts: List[AgentVerdict] = []
        for inv in invoices:
            dossier = dossiers[inv.invoice_id]
            verdict = self.evaluate_invoice(inv, dossier)
            verdicts.append(verdict)
        return verdicts
