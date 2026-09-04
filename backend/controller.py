import os
from typing import List, Dict, Tuple, Any, Optional
from datetime import datetime, timedelta
from backend.models import (
    Invoice, EvidenceDossier, FinanceException, ExceptionGroup,
    BankChangeAlert, CashPositionSummary, CashOutflowBucket,
    PaymentStatus, ExceptionSeverity, ExceptionOwner, ControlStatus,
    FinanceControlPolicy, VendorMaster
)

HISTORICAL_RESOLUTION_PATTERNS = {
    "MISSING_GRN": {
        "similar_count": 8,
        "resolved_count": 7,
        "most_common_action": "Request warehouse receiving confirmation from Logistics Supervisor"
    },
    "QUANTITY_MISMATCH": {
        "similar_count": 6,
        "resolved_count": 5,
        "most_common_action": "Request revised invoice for received quantity or apply credit memo"
    },
    "PRICE_MISMATCH": {
        "similar_count": 4,
        "resolved_count": 3,
        "most_common_action": "Require Buyer signoff on contract rate variance"
    },
    "EXTRA_LINE_ITEM": {
        "similar_count": 5,
        "resolved_count": 4,
        "most_common_action": "Issue revised PO or obtain Controller signoff on ancillary freight"
    },
    "BANK_CHANGE_RISK": {
        "similar_count": 3,
        "resolved_count": 0,
        "most_common_action": "Freeze payment and execute out-of-band phone callback to vendor CFO"
    },
    "STRUCTURING_ATTACK": {
        "similar_count": 2,
        "resolved_count": 0,
        "most_common_action": "Freeze vendor account and escalate to Internal Audit / Legal"
    },
    "DUPLICATE_INVOICE": {
        "similar_count": 9,
        "resolved_count": 9,
        "most_common_action": "Void and cancel duplicate entry to prevent double disbursement"
    },
    "PO_VARIANCE": {
        "similar_count": 7,
        "resolved_count": 6,
        "most_common_action": "Route to Department Budget Holder for PO amendment"
    },
    "COLLUSION_RISK": {
        "similar_count": 2,
        "resolved_count": 0,
        "most_common_action": "Hold disbursements and conduct vendor master audit"
    },
    "FIRST_TIME_LARGE_BILL": {
        "similar_count": 5,
        "resolved_count": 4,
        "most_common_action": "Verify W-9 tax documentation and Procurement contract agreement"
    }
}

class FinanceOperationsController:
    """
    Core Controller Engine for:
    - Deterministic Exception Resolution & Prioritization
    - Vendor-Level Exception Grouping & Bulk Aggregation
    - Payment Queue Classification & Gatekeeping
    - Forward-Looking Cash Outflow Forecasting (7d, 14d, 30d)
    - Multi-Step Bank Change / BEC Verification Workflow
    """

    def __init__(self, policy: Optional[FinanceControlPolicy] = None):
        self.policy = policy or FinanceControlPolicy()

    def generate_exceptions(
        self,
        invoices: List[Invoice],
        dossiers: Dict[str, EvidenceDossier]
    ) -> List[FinanceException]:
        exceptions: List[FinanceException] = []
        base_time = datetime(2026, 8, 20, 10, 0, 0)

        for inv in invoices:
            d = dossiers[inv.invoice_id]

            # 1. Cross-Batch Structuring Attack
            if d.structuring_evidence.in_structuring_cluster:
                s_ev = d.structuring_evidence
                ex = FinanceException(
                    exception_id=f"EXC-STRUC-{inv.invoice_id}",
                    invoice_id=inv.invoice_id,
                    vendor_name=inv.vendor_name,
                    vendor_id=inv.vendor_id,
                    invoice_amount=inv.amount,
                    exception_type="STRUCTURING_ATTACK",
                    severity="CRITICAL",
                    priority_score=98.5,
                    financial_impact=s_ev.cluster_total_amount,
                    affected_records=s_ev.cluster_invoice_ids,
                    evidence_summary=s_ev.pattern_description or "Structuring evasion",
                    recommended_action="Freeze all disbursements immediately. Route to Internal Audit and Corporate Security.",
                    suggested_owner="INTERNAL_AUDIT",
                    status="OPEN",
                    created_at=base_time.strftime("%Y-%m-%d %H:%M:%S"),
                    resolution_deadline=(base_time + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S"),
                    historical_precedent=HISTORICAL_RESOLUTION_PATTERNS.get("STRUCTURING_ATTACK")
                )
                exceptions.append(ex)
                continue

            # 2. BEC Bank Fingerprint Change Risk
            if d.bank_evidence.risk_level == "HIGH_RISK_RECENT_CHANGE":
                b_ev = d.bank_evidence
                ex = FinanceException(
                    exception_id=f"EXC-BEC-{inv.invoice_id}",
                    invoice_id=inv.invoice_id,
                    vendor_name=inv.vendor_name,
                    vendor_id=inv.vendor_id,
                    invoice_amount=inv.amount,
                    exception_type="BANK_CHANGE_RISK",
                    severity="CRITICAL",
                    priority_score=95.0,
                    financial_impact=inv.amount,
                    affected_records=[inv.invoice_id],
                    evidence_summary=b_ev.details,
                    recommended_action="Place on Payment Hold. Execute out-of-band verbal phone callback to verified vendor CFO.",
                    suggested_owner="CONTROLLER",
                    status="OPEN",
                    created_at=base_time.strftime("%Y-%m-%d %H:%M:%S"),
                    resolution_deadline=(base_time + timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S"),
                    historical_precedent=HISTORICAL_RESOLUTION_PATTERNS.get("BANK_CHANGE_RISK")
                )
                exceptions.append(ex)
                continue

            # 3. Vendor Collusion Risk
            if d.collusion_evidence.shared_fingerprint_detected:
                c_ev = d.collusion_evidence
                ex = FinanceException(
                    exception_id=f"EXC-COL-{inv.invoice_id}",
                    invoice_id=inv.invoice_id,
                    vendor_name=inv.vendor_name,
                    vendor_id=inv.vendor_id,
                    invoice_amount=inv.amount,
                    exception_type="COLLUSION_RISK",
                    severity="HIGH",
                    priority_score=88.0,
                    financial_impact=inv.amount,
                    affected_records=[inv.invoice_id],
                    evidence_summary=c_ev.details,
                    recommended_action="Audit vendor master entity linkages; hold payment pending tax ID & owner verification.",
                    suggested_owner="CONTROLLER",
                    status="OPEN",
                    created_at=base_time.strftime("%Y-%m-%d %H:%M:%S"),
                    resolution_deadline=(base_time + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
                    historical_precedent=HISTORICAL_RESOLUTION_PATTERNS.get("COLLUSION_RISK")
                )
                exceptions.append(ex)
                continue

            # 4. Duplicate Invoices
            if d.duplicate_evidence.is_duplicate_risk:
                dup_ev = d.duplicate_evidence
                top_cand = dup_ev.candidates[0] if dup_ev.candidates else None
                cand_id = top_cand.matched_invoice_id if top_cand else "prior record"
                ex = FinanceException(
                    exception_id=f"EXC-DUP-{inv.invoice_id}",
                    invoice_id=inv.invoice_id,
                    vendor_name=inv.vendor_name,
                    vendor_id=inv.vendor_id,
                    invoice_amount=inv.amount,
                    exception_type="DUPLICATE_INVOICE",
                    severity="HIGH",
                    priority_score=82.0,
                    financial_impact=inv.amount,
                    affected_records=[inv.invoice_id, cand_id],
                    evidence_summary=dup_ev.details,
                    recommended_action=f"Cancel and void duplicate invoice {inv.invoice_id} to prevent double disbursement of ${inv.amount:,.2f}.",
                    suggested_owner="AP_CLERK",
                    status="OPEN",
                    created_at=base_time.strftime("%Y-%m-%d %H:%M:%S"),
                    resolution_deadline=(base_time + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
                    historical_precedent=HISTORICAL_RESOLUTION_PATTERNS.get("DUPLICATE_INVOICE")
                )
                exceptions.append(ex)
                continue

            # 5. 3-Way Reconciliation Exceptions
            rcpt_ev = d.receipt_evidence
            if rcpt_ev.match_status == "MISSING_GRN":
                ex = FinanceException(
                    exception_id=f"EXC-GRN-{inv.invoice_id}",
                    invoice_id=inv.invoice_id,
                    vendor_name=inv.vendor_name,
                    vendor_id=inv.vendor_id,
                    invoice_amount=inv.amount,
                    exception_type="MISSING_GRN",
                    severity="MEDIUM",
                    priority_score=68.0,
                    financial_impact=inv.amount,
                    affected_records=[inv.invoice_id, inv.po_reference or ""],
                    evidence_summary=rcpt_ev.details,
                    recommended_action="Contact receiving dock / logistics to confirm whether goods arrived and generate GRN.",
                    suggested_owner="AP_CLERK",
                    status="OPEN",
                    created_at=base_time.strftime("%Y-%m-%d %H:%M:%S"),
                    resolution_deadline=(base_time + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"),
                    historical_precedent=HISTORICAL_RESOLUTION_PATTERNS.get("MISSING_GRN")
                )
                exceptions.append(ex)
            elif rcpt_ev.match_status in ["QUANTITY_OVERBILLED", "PARTIAL_RECEIPT_OVERBILL"]:
                ex = FinanceException(
                    exception_id=f"EXC-QTY-{inv.invoice_id}",
                    invoice_id=inv.invoice_id,
                    vendor_name=inv.vendor_name,
                    vendor_id=inv.vendor_id,
                    invoice_amount=inv.amount,
                    exception_type="QUANTITY_MISMATCH",
                    severity="HIGH",
                    priority_score=75.0,
                    financial_impact=abs(rcpt_ev.qty_discrepancy * (inv.amount / max(rcpt_ev.invoice_qty_total, 1))),
                    affected_records=[inv.invoice_id, inv.po_reference or "", rcpt_ev.grn_id or ""],
                    evidence_summary=rcpt_ev.details,
                    recommended_action="Short-pay invoice for received quantity only or request supplier credit memo.",
                    suggested_owner="AP_CLERK",
                    status="OPEN",
                    created_at=base_time.strftime("%Y-%m-%d %H:%M:%S"),
                    resolution_deadline=(base_time + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
                    historical_precedent=HISTORICAL_RESOLUTION_PATTERNS.get("QUANTITY_MISMATCH")
                )
                exceptions.append(ex)
            elif rcpt_ev.match_status == "PRICE_MISMATCH":
                ex = FinanceException(
                    exception_id=f"EXC-PRICE-{inv.invoice_id}",
                    invoice_id=inv.invoice_id,
                    vendor_name=inv.vendor_name,
                    vendor_id=inv.vendor_id,
                    invoice_amount=inv.amount,
                    exception_type="PRICE_MISMATCH",
                    severity="MEDIUM",
                    priority_score=64.0,
                    financial_impact=rcpt_ev.price_discrepancy,
                    affected_records=[inv.invoice_id, inv.po_reference or ""],
                    evidence_summary=rcpt_ev.details,
                    recommended_action="Route to Procurement Buyer to enforce contracted PO rate or authorize price adjustment.",
                    suggested_owner="PROCUREMENT_BUYER",
                    status="OPEN",
                    created_at=base_time.strftime("%Y-%m-%d %H:%M:%S"),
                    resolution_deadline=(base_time + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
                    historical_precedent=HISTORICAL_RESOLUTION_PATTERNS.get("PRICE_MISMATCH")
                )
                exceptions.append(ex)
            elif rcpt_ev.match_status == "EXTRA_LINE_ITEM":
                ex = FinanceException(
                    exception_id=f"EXC-EXTRA-{inv.invoice_id}",
                    invoice_id=inv.invoice_id,
                    vendor_name=inv.vendor_name,
                    vendor_id=inv.vendor_id,
                    invoice_amount=inv.amount,
                    exception_type="EXTRA_LINE_ITEM",
                    severity="MEDIUM",
                    priority_score=62.0,
                    financial_impact=rcpt_ev.price_discrepancy,
                    affected_records=[inv.invoice_id, inv.po_reference or ""],
                    evidence_summary=rcpt_ev.details,
                    recommended_action="Reject unapproved surcharge line items or request updated PO from Buyer.",
                    suggested_owner="PROCUREMENT_BUYER",
                    status="OPEN",
                    created_at=base_time.strftime("%Y-%m-%d %H:%M:%S"),
                    resolution_deadline=(base_time + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"),
                    historical_precedent=HISTORICAL_RESOLUTION_PATTERNS.get("EXTRA_LINE_ITEM")
                )
                exceptions.append(ex)

            # 6. PO Tolerance Variance Exception
            if d.po_evidence.status == "AMOUNT_EXCEEDED":
                p_ev = d.po_evidence
                ex = FinanceException(
                    exception_id=f"EXC-POVAR-{inv.invoice_id}",
                    invoice_id=inv.invoice_id,
                    vendor_name=inv.vendor_name,
                    vendor_id=inv.vendor_id,
                    invoice_amount=inv.amount,
                    exception_type="PO_VARIANCE",
                    severity="MEDIUM",
                    priority_score=60.0,
                    financial_impact=p_ev.amount_difference or 0.0,
                    affected_records=[inv.invoice_id, p_ev.po_number or ""],
                    evidence_summary=p_ev.details,
                    recommended_action="Hold payment. Route to Department Budget Holder to approve invoice overage.",
                    suggested_owner="PROCUREMENT_BUYER",
                    status="OPEN",
                    created_at=base_time.strftime("%Y-%m-%d %H:%M:%S"),
                    resolution_deadline=(base_time + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"),
                    historical_precedent=HISTORICAL_RESOLUTION_PATTERNS.get("PO_VARIANCE")
                )
                exceptions.append(ex)

            # 7. First-Time Large Vendor Exception
            if d.vendor_history_evidence.is_unusually_large_first_time:
                ex = FinanceException(
                    exception_id=f"EXC-NEWVEND-{inv.invoice_id}",
                    invoice_id=inv.invoice_id,
                    vendor_name=inv.vendor_name,
                    vendor_id=inv.vendor_id,
                    invoice_amount=inv.amount,
                    exception_type="FIRST_TIME_LARGE_BILL",
                    severity="HIGH",
                    priority_score=78.0,
                    financial_impact=inv.amount,
                    affected_records=[inv.invoice_id],
                    evidence_summary=d.vendor_history_evidence.details,
                    recommended_action="Require Controller onboarding verification, W-9 validation, and Master Services Agreement review.",
                    suggested_owner="CONTROLLER",
                    status="OPEN",
                    created_at=base_time.strftime("%Y-%m-%d %H:%M:%S"),
                    resolution_deadline=(base_time + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
                    historical_precedent=HISTORICAL_RESOLUTION_PATTERNS.get("FIRST_TIME_LARGE_BILL")
                )
                exceptions.append(ex)

        # Sort exceptions by priority score descending
        exceptions.sort(key=lambda x: x.priority_score, reverse=True)
        return exceptions

    def group_exceptions(self, exceptions: List[FinanceException]) -> List[ExceptionGroup]:
        """
        Groups individual row exceptions into higher-level operational issues
        (e.g., 'Apex Security: 4 Structuring Split Invoices' or 'Datasync: 2 PO Variance Exceptions').
        """
        grouped_dict: Dict[Tuple[str, str], List[FinanceException]] = {}
        for ex in exceptions:
            key = (ex.vendor_id, ex.exception_type)
            if key not in grouped_dict:
                grouped_dict[key] = []
            grouped_dict[key].append(ex)

        groups: List[ExceptionGroup] = []
        for (v_id, exc_type), ex_list in grouped_dict.items():
            first = ex_list[0]
            total_impact = sum(e.financial_impact for e in ex_list)
            inv_ids = [e.invoice_id for e in ex_list]
            
            title = f"{first.vendor_name}: {len(ex_list)} {exc_type.replace('_', ' ').title()} Issue(s)"
            pattern_summary = f"{len(ex_list)} invoice(s) with combined ${total_impact:,.2f} exposure requiring {first.suggested_owner} review."

            groups.append(ExceptionGroup(
                group_id=f"GRP-{v_id}-{exc_type}",
                title=title,
                vendor_name=first.vendor_name,
                vendor_id=v_id,
                exception_type=exc_type,
                invoice_count=len(ex_list),
                total_financial_impact=round(total_impact, 2),
                invoice_ids=inv_ids,
                recommended_bulk_action=first.recommended_action,
                severity=first.severity,
                pattern_summary=pattern_summary
            ))

        groups.sort(key=lambda g: g.total_financial_impact, reverse=True)
        return groups

    def generate_bank_change_alerts(
        self,
        invoices: List[Invoice],
        vendor_masters: List[VendorMaster],
        recent_bank_changes: Dict[str, int]
    ) -> List[BankChangeAlert]:
        alerts: List[BankChangeAlert] = []
        vendor_map = {v.vendor_id: v for v in vendor_masters}

        for v_id, days_ago in recent_bank_changes.items():
            vendor = vendor_map.get(v_id)
            if not vendor: continue
            
            # Find affected invoices
            affected_invs = [inv for inv in invoices if inv.vendor_id == v_id and inv.vendor_bank_fingerprint != vendor.primary_bank_fingerprint]
            affected_ids = [inv.invoice_id for inv in affected_invs]
            total_val = sum(inv.amount for inv in affected_invs)

            if affected_invs:
                alert = BankChangeAlert(
                    vendor_id=v_id,
                    vendor_name=vendor.vendor_name,
                    old_fingerprint=vendor.primary_bank_fingerprint,
                    new_fingerprint=affected_invs[0].vendor_bank_fingerprint,
                    days_since_change=days_ago,
                    affected_invoice_ids=affected_ids,
                    affected_payment_value=round(total_val, 2),
                    risk_severity="CRITICAL",
                    independent_phone_verified="PENDING",
                    cfo_signoff="PENDING",
                    account_ownership_verified="PENDING",
                    cooling_period_elapsed="PENDING" if days_ago < self.policy.bank_cooling_days else "VERIFIED",
                    all_controls_satisfied=False
                )
                alerts.append(alert)

        return alerts

    def update_payment_queue_and_cash_position(
        self,
        invoices: List[Invoice],
        dossiers: Dict[str, EvidenceDossier],
        bank_alerts: List[BankChangeAlert]
    ) -> CashPositionSummary:
        """
        Classifies payment queue statuses and calculates deterministic AP cash exposure.
        Forecasts 0-7d, 8-14d, 15-30d, 30+d outflows separated into Approved vs Held vs High-Risk.
        """
        base_date = datetime(2026, 8, 20)
        
        total_approved = 0.0
        total_held = 0.0
        total_fraud_risk = 0.0
        total_dup_prevented = 0.0
        overdue_payable = 0.0
        due_7d = 0.0
        due_14d = 0.0
        due_30d = 0.0

        # Outflow buckets
        buckets = {
            "0-7 Days": {"approved": 0.0, "held": 0.0, "high_risk": 0.0},
            "8-14 Days": {"approved": 0.0, "held": 0.0, "high_risk": 0.0},
            "15-30 Days": {"approved": 0.0, "held": 0.0, "high_risk": 0.0},
            "30+ Days": {"approved": 0.0, "held": 0.0, "high_risk": 0.0}
        }

        for inv in invoices:
            d = dossiers[inv.invoice_id]
            inv_due = datetime.strptime(inv.due_date, "%Y-%m-%d")
            days_until_due = (inv_due - base_date).days

            # Determine payment status
            if d.structuring_evidence.in_structuring_cluster:
                inv.payment_status = "FRAUD_HOLD"
                inv.approval_status = "ESCALATED"
                total_fraud_risk += inv.amount
                risk_tier = "high_risk"
            elif d.bank_evidence.risk_level == "HIGH_RISK_RECENT_CHANGE":
                inv.payment_status = "FRAUD_HOLD"
                inv.approval_status = "ESCALATED"
                total_fraud_risk += inv.amount
                risk_tier = "high_risk"
            elif d.collusion_evidence.shared_fingerprint_detected:
                inv.payment_status = "FRAUD_HOLD"
                inv.approval_status = "ESCALATED"
                total_fraud_risk += inv.amount
                risk_tier = "high_risk"
            elif d.duplicate_evidence.is_duplicate_risk:
                inv.payment_status = "DUPLICATE_REJECTED"
                inv.approval_status = "REJECTED"
                total_dup_prevented += inv.amount
                risk_tier = "held" # Blocked
            elif d.receipt_evidence.match_status == "MISSING_GRN":
                inv.payment_status = "MISSING_DOCUMENTATION"
                inv.approval_status = "PENDING"
                total_held += inv.amount
                risk_tier = "held"
            elif d.receipt_evidence.match_status in ["QUANTITY_OVERBILLED", "PARTIAL_RECEIPT_OVERBILL", "PRICE_MISMATCH", "EXTRA_LINE_ITEM"]:
                inv.payment_status = "BLOCKED_BY_RECONCILIATION"
                inv.approval_status = "PENDING"
                total_held += inv.amount
                risk_tier = "held"
            elif d.po_evidence.status == "AMOUNT_EXCEEDED" or d.vendor_history_evidence.is_unusually_large_first_time:
                inv.payment_status = "AWAITING_REVIEW"
                inv.approval_status = "PENDING"
                total_held += inv.amount
                risk_tier = "held"
            else:
                inv.payment_status = "READY_FOR_PAYMENT"
                inv.approval_status = "APPROVED"
                total_approved += inv.amount
                risk_tier = "approved"

            # Due date tracking
            if days_until_due < 0:
                overdue_payable += inv.amount
            if 0 <= days_until_due <= 7:
                due_7d += inv.amount
            if 0 <= days_until_due <= 14:
                due_14d += inv.amount
            if 0 <= days_until_due <= 30:
                due_30d += inv.amount

            # Assign to bucket
            if days_until_due <= 7:
                b_name = "0-7 Days"
            elif days_until_due <= 14:
                b_name = "8-14 Days"
            elif days_until_due <= 30:
                b_name = "15-30 Days"
            else:
                b_name = "30+ Days"

            buckets[b_name][risk_tier] += inv.amount

        # Build Outflow Bucket objects
        forecast_list: List[CashOutflowBucket] = []
        for b_name, data in buckets.items():
            tot = data["approved"] + data["held"] + data["high_risk"]
            forecast_list.append(CashOutflowBucket(
                days_range=b_name,
                label=f"Projected Outflow ({b_name})",
                approved_amount=round(data["approved"], 2),
                held_amount=round(data["held"], 2),
                high_risk_amount=round(data["high_risk"], 2),
                total_projected_outflow=round(tot, 2)
            ))

        cash_at_risk = round(total_held + total_fraud_risk, 2)

        return CashPositionSummary(
            total_approved_payable=round(total_approved, 2),
            total_held_payable=round(total_held, 2),
            total_fraud_risk_payable=round(total_fraud_risk, 2),
            total_duplicate_prevented=round(total_dup_prevented, 2),
            overdue_payable=round(overdue_payable, 2),
            payable_due_7d=round(due_7d, 2),
            payable_due_14d=round(due_14d, 2),
            payable_due_30d=round(due_30d, 2),
            cash_at_risk=cash_at_risk,
            outflow_forecast=forecast_list
        )
