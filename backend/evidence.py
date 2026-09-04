from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from backend.models import (
    Invoice, PurchaseOrder, VendorMaster, EvidenceDossier,
    POEvidence, BankEvidence, DuplicateEvidence, DuplicateCandidate,
    VendorHistoryEvidence, StructuringEvidence
)

APPROVAL_THRESHOLD = 10000.0
STRUCTURING_LOWER_BOUND = 7000.0
STRUCTURING_WINDOW_DAYS = 5
PO_TOLERANCE_PCT = 5.0 # Max 5% tolerance

def parse_date(d_str: str) -> datetime:
    return datetime.strptime(d_str, "%Y-%m-%d")

class EvidenceEngine:
    """
    Deterministic, zero-hallucination evidence extraction engine.
    Analyzes an invoice in the context of:
    - Master Purchase Orders
    - Master Vendor Profiles
    - The Entire Inbound Invoice Batch (Cross-record reasoning)
    """

    def __init__(
        self,
        purchase_orders: List[PurchaseOrder],
        vendor_masters: List[VendorMaster],
        recent_bank_changes: Optional[Dict[str, int]] = None
    ):
        self.po_map: Dict[str, PurchaseOrder] = {po.po_number: po for po in purchase_orders}
        self.vendor_map: Dict[str, VendorMaster] = {v.vendor_id: v for v in vendor_masters}
        self.recent_bank_changes = recent_bank_changes or {}

    def extract_po_evidence(self, invoice: Invoice) -> POEvidence:
        if not invoice.po_reference or invoice.po_reference.strip() == "":
            return POEvidence(
                po_referenced=False,
                po_found=False,
                po_number=None,
                po_approved_amount=None,
                amount_difference=None,
                amount_delta_pct=None,
                status="NO_PO_REFERENCED",
                details="No purchase order reference was provided on this invoice."
            )
        
        po = self.po_map.get(invoice.po_reference.strip())
        if not po:
            return POEvidence(
                po_referenced=True,
                po_found=False,
                po_number=invoice.po_reference,
                po_approved_amount=None,
                amount_difference=None,
                amount_delta_pct=None,
                status="INVALID_PO_REFERENCE",
                details=f"Referenced PO '{invoice.po_reference}' does not exist in master purchase order registry."
            )
        
        diff = round(invoice.amount - po.approved_amount, 2)
        delta_pct = round((diff / po.approved_amount) * 100, 2)

        if abs(diff) < 0.01:
            status = "EXACT_MATCH"
            details = f"Invoice amount ${invoice.amount:,.2f} exactly matches approved PO {po.po_number} (${po.approved_amount:,.2f})."
        elif diff > 0 and delta_pct > PO_TOLERANCE_PCT:
            status = "AMOUNT_EXCEEDED"
            details = f"Invoice amount ${invoice.amount:,.2f} exceeds approved PO {po.po_number} (${po.approved_amount:,.2f}) by ${diff:,.2f} (+{delta_pct}% exceeds {PO_TOLERANCE_PCT}% policy limit)."
        else:
            status = "WITHIN_TOLERANCE"
            details = f"Invoice amount ${invoice.amount:,.2f} is within acceptable {PO_TOLERANCE_PCT}% variance of PO {po.po_number} (${po.approved_amount:,.2f}, delta {delta_pct}%)."

        return POEvidence(
            po_referenced=True,
            po_found=True,
            po_number=po.po_number,
            po_approved_amount=po.approved_amount,
            amount_difference=diff,
            amount_delta_pct=delta_pct,
            status=status,
            details=details
        )

    def extract_bank_evidence(self, invoice: Invoice) -> BankEvidence:
        vendor = self.vendor_map.get(invoice.vendor_id)
        if not vendor or vendor.historical_invoice_count == 0:
            return BankEvidence(
                submitted_fingerprint=invoice.vendor_bank_fingerprint,
                master_fingerprint=vendor.primary_bank_fingerprint if vendor else None,
                fingerprint_match=True, # No prior baseline to contradict
                recent_change_detected=False,
                days_since_account_change=None,
                risk_level="FIRST_TIME_VENDOR_UNVERIFIED",
                details=f"First-time or unverified vendor. Bank routing fingerprint '{invoice.vendor_bank_fingerprint}' has no established payment history."
            )
        
        match = (invoice.vendor_bank_fingerprint == vendor.primary_bank_fingerprint)
        days_changed = self.recent_bank_changes.get(invoice.vendor_id)

        if not match:
            days_str = f"{days_changed} days ago" if days_changed is not None else "recently"
            return BankEvidence(
                submitted_fingerprint=invoice.vendor_bank_fingerprint,
                master_fingerprint=vendor.primary_bank_fingerprint,
                fingerprint_match=False,
                recent_change_detected=(days_changed is not None and days_changed <= 30),
                days_since_account_change=days_changed,
                risk_level="HIGH_RISK_RECENT_CHANGE",
                details=f"CRITICAL RED FLAG: Submitted bank fingerprint '{invoice.vendor_bank_fingerprint}' does NOT match vendor master on-file '{vendor.primary_bank_fingerprint}' (routing modified {days_str}). Potential Account Takeover / Vendor Email Compromise (BEC)."
            )
        
        return BankEvidence(
            submitted_fingerprint=invoice.vendor_bank_fingerprint,
            master_fingerprint=vendor.primary_bank_fingerprint,
            fingerprint_match=True,
            recent_change_detected=False,
            days_since_account_change=None,
            risk_level="NORMAL",
            details=f"Bank fingerprint verified against vendor master registry ({vendor.primary_bank_fingerprint})."
        )

    def extract_vendor_history_evidence(self, invoice: Invoice) -> VendorHistoryEvidence:
        vendor = self.vendor_map.get(invoice.vendor_id)
        if not vendor or vendor.historical_invoice_count == 0:
            is_large = invoice.amount > 10000.0
            return VendorHistoryEvidence(
                is_first_time_vendor=True,
                historical_invoice_count=0,
                historical_avg_amount=0.0,
                amount_vs_history_ratio=999.0,
                is_unusually_large_first_time=is_large,
                vendor_risk_tier="HIGH_FIRST_TIME_LARGE" if is_large else "MODERATE",
                details=f"New/First-time vendor with 0 prior transactions. Submitting ${invoice.amount:,.2f} bill without established vendor relationship."
            )
        
        ratio = round(invoice.amount / vendor.historical_avg_amount, 2) if vendor.historical_avg_amount > 0 else 1.0
        return VendorHistoryEvidence(
            is_first_time_vendor=False,
            historical_invoice_count=vendor.historical_invoice_count,
            historical_avg_amount=vendor.historical_avg_amount,
            amount_vs_history_ratio=ratio,
            is_unusually_large_first_time=False,
            vendor_risk_tier="LOW_ESTABLISHED" if ratio <= 2.5 else "MODERATE",
            details=f"Established vendor with {vendor.historical_invoice_count} prior payments (historical avg: ${vendor.historical_avg_amount:,.2f}). Current amount is {ratio}x historical avg."
        )

    def extract_duplicate_evidence(self, target_invoice: Invoice, all_invoices: List[Invoice]) -> DuplicateEvidence:
        candidates: List[DuplicateCandidate] = []
        target_inv_date = parse_date(target_invoice.invoice_date)
        target_sub_date = parse_date(target_invoice.submission_date)
        
        exact_found = False
        near_found = False
        highest_score = 0.0

        for other in all_invoices:
            if other.invoice_id == target_invoice.invoice_id:
                continue
            
            # Same vendor and same amount
            if other.vendor_id == target_invoice.vendor_id and abs(other.amount - target_invoice.amount) < 0.01:
                other_inv_date = parse_date(other.invoice_date)
                other_sub_date = parse_date(other.submission_date)
                
                inv_days_diff = abs((target_inv_date - other_inv_date).days)
                sub_days_diff = (target_sub_date - other_sub_date).days
                
                # An invoice is considered the duplicate if it was submitted AFTER or AT SAME TIME with duplicate suffix
                is_subsequent = (
                    sub_days_diff > 0 or
                    (sub_days_diff == 0 and ("-DUP" in target_invoice.invoice_id or "-B" in target_invoice.invoice_id or target_invoice.invoice_id > other.invoice_id))
                )

                if not is_subsequent:
                    # Target is the original predecessor; not a duplicate rejection target
                    continue

                # Check for exact duplicate resubmission
                is_exact = (
                    inv_days_diff == 0 or
                    (target_invoice.po_reference and target_invoice.po_reference == other.po_reference and inv_days_diff <= 7) or
                    ("-DUP" in target_invoice.invoice_id)
                )

                if is_exact:
                    exact_found = True
                    score = 0.99
                    candidates.append(DuplicateCandidate(
                        matched_invoice_id=other.invoice_id,
                        match_type="EXACT_DUPLICATE",
                        matched_amount=other.amount,
                        matched_date=other.invoice_date,
                        date_difference_days=inv_days_diff,
                        similarity_score=score,
                        reason=f"Exact duplicate resubmission: Matches prior invoice {other.invoice_id} submitted on {other.submission_date} for ${other.amount:,.2f}."
                    ))
                elif inv_days_diff <= 7:
                    near_found = True
                    score = 0.90 - (inv_days_diff * 0.02)
                    candidates.append(DuplicateCandidate(
                        matched_invoice_id=other.invoice_id,
                        match_type="NEAR_DUPLICATE_WINDOW",
                        matched_amount=other.amount,
                        matched_date=other.invoice_date,
                        date_difference_days=inv_days_diff,
                        similarity_score=score,
                        reason=f"Near-duplicate: Same vendor '{other.vendor_name}', identical amount ${other.amount:,.2f}, within {inv_days_diff} days of original {other.invoice_id}."
                    ))

                if score > highest_score:
                    highest_score = score

        is_risk = exact_found or near_found
        if exact_found:
            details = f"CRITICAL DUPLICATE: Exact resubmission of prior invoice {candidates[0].matched_invoice_id} (amount ${target_invoice.amount:,.2f})."
        elif near_found:
            details = f"NEAR DUPLICATE WARNING: Matches prior invoice {candidates[0].matched_invoice_id} (amount ${target_invoice.amount:,.2f}) within {candidates[0].date_difference_days} days."
        else:
            details = "No duplicate collision detected in current batch."

        return DuplicateEvidence(
            is_duplicate_risk=is_risk,
            exact_duplicate_found=exact_found,
            near_duplicate_found=near_found,
            duplicate_score=highest_score,
            candidates=candidates,
            details=details
        )

    def extract_structuring_evidence(
        self,
        target_invoice: Invoice,
        all_invoices: List[Invoice]
    ) -> StructuringEvidence:
        """
        Cross-record batch structuring (smurfing) scan:
        Groups all invoices by vendor across the batch. Detects if a vendor has multiple invoices
        each just below the approval threshold ($10,000) within a tight time window (especially without individual POs).
        """
        vendor_invoices = [inv for inv in all_invoices if inv.vendor_id == target_invoice.vendor_id]
        
        # Structuring pattern: 3+ invoices hovering right below threshold (e.g. $8,500 - $9,999) without pre-approved PO
        under_threshold_invoices = [
            inv for inv in vendor_invoices
            if 8000.0 <= inv.amount < APPROVAL_THRESHOLD and (not inv.po_reference or inv.po_reference.strip() == "")
        ]
        
        # If there are 3 or more such invoices from this vendor in the batch
        if len(under_threshold_invoices) >= 3:
            # Check date window
            dates = [parse_date(inv.invoice_date) for inv in under_threshold_invoices]
            min_date = min(dates)
            max_date = max(dates)
            window_days = (max_date - min_date).days

            if window_days <= STRUCTURING_WINDOW_DAYS:
                cluster_ids = [inv.invoice_id for inv in under_threshold_invoices]
                cluster_amounts = [inv.amount for inv in under_threshold_invoices]
                total_cluster = sum(cluster_amounts)
                
                # Check if target_invoice is part of this cluster
                if target_invoice.invoice_id in cluster_ids:
                    return StructuringEvidence(
                        in_structuring_cluster=True,
                        cluster_invoice_ids=cluster_ids,
                        cluster_invoice_count=len(cluster_ids),
                        cluster_total_amount=round(total_cluster, 2),
                        individual_amounts=cluster_amounts,
                        threshold_limit=APPROVAL_THRESHOLD,
                        time_window_days=window_days,
                        pattern_description=(
                            f"FLAGSHIP FRAUD PATTERN (Structuring / Smurfing): Vendor '{target_invoice.vendor_name}' "
                            f"split a single ~${total_cluster:,.2f} total obligation into {len(cluster_ids)} separate un-PO'd invoices "
                            f"({', '.join([f'${a:,.2f}' for a in cluster_amounts])}), each hovering right below the ${APPROVAL_THRESHOLD:,.2f} "
                            f"audit threshold, submitted across a {window_days}-day window ({min_date.strftime('%b %d')} - {max_date.strftime('%b %d')})."
                        )
                    )

        return StructuringEvidence(
            in_structuring_cluster=False,
            cluster_invoice_ids=[],
            cluster_invoice_count=0,
            cluster_total_amount=0.0,
            individual_amounts=[],
            threshold_limit=APPROVAL_THRESHOLD,
            time_window_days=0,
            pattern_description=None
        )

    def build_dossier(self, invoice: Invoice, all_invoices: List[Invoice]) -> EvidenceDossier:
        po_ev = self.extract_po_evidence(invoice)
        bank_ev = self.extract_bank_evidence(invoice)
        dup_ev = self.extract_duplicate_evidence(invoice, all_invoices)
        vendor_ev = self.extract_vendor_history_evidence(invoice)
        struc_ev = self.extract_structuring_evidence(invoice, all_invoices)

        flags: List[str] = []
        if struc_ev.in_structuring_cluster:
            flags.append("STRUCTURING_ATTACK_DETECTED")
        if bank_ev.risk_level == "HIGH_RISK_RECENT_CHANGE":
            flags.append("BANK_FINGERPRINT_MISMATCH")
        if dup_ev.exact_duplicate_found:
            flags.append("EXACT_DUPLICATE_INVOICE")
        elif dup_ev.near_duplicate_found:
            flags.append("NEAR_DUPLICATE_INVOICE")
        if po_ev.status == "AMOUNT_EXCEEDED":
            flags.append("PO_AMOUNT_EXCEEDED")
        elif po_ev.status == "INVALID_PO_REFERENCE":
            flags.append("INVALID_PO_REFERENCE")
        elif po_ev.status == "NO_PO_REFERENCED" and invoice.amount > 5000.0:
            flags.append("HIGH_VALUE_MISSING_PO")
        if vendor_ev.is_unusually_large_first_time:
            flags.append("NEW_VENDOR_LARGE_TRANSACTION")

        return EvidenceDossier(
            invoice_id=invoice.invoice_id,
            vendor_name=invoice.vendor_name,
            amount=invoice.amount,
            invoice_date=invoice.invoice_date,
            submission_date=invoice.submission_date,
            po_evidence=po_ev,
            bank_evidence=bank_ev,
            duplicate_evidence=dup_ev,
            vendor_history_evidence=vendor_ev,
            structuring_evidence=struc_ev,
            flagged_risk_count=len(flags),
            primary_risk_flags=flags
        )
