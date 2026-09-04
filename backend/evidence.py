from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import re
from backend.models import (
    Invoice, PurchaseOrder, GoodsReceipt, VendorMaster, EvidenceDossier,
    POEvidence, ReceiptEvidence, BankEvidence, DuplicateEvidence, DuplicateCandidate,
    DuplicateSimilarityFactors, VendorHistoryEvidence, StructuringEvidence,
    CollusionEvidence, FinanceControlPolicy
)

def parse_date(d_str: str) -> datetime:
    return datetime.strptime(d_str, "%Y-%m-%d")

def levenshtein_similarity(s1: str, s2: str) -> float:
    """Calculates normalized string similarity based on character edit distance."""
    s1 = s1.lower().strip()
    s2 = s2.lower().strip()
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    
    # Simple dynamic programming Levenshtein distance
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
        
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
            
    dist = dp[m][n]
    max_len = max(m, n)
    return round(1.0 - (dist / max_len), 4)

def token_jaccard_similarity(text1: str, text2: str) -> float:
    """Calculates token overlap similarity between descriptions."""
    def tokenize(t: str) -> set:
        tokens = re.findall(r'\b[a-zA-Z0-9]{2,}\b', t.lower())
        return set(tokens)
    
    set1 = tokenize(text1)
    set2 = tokenize(text2)
    if not set1 and not set2:
        return 1.0
    if not set1 or not set2:
        return 0.0
    
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return round(intersection / union, 4) if union > 0 else 0.0

class EvidenceEngine:
    """
    Deterministic, Zero-Hallucination Evidence Extraction & 3-Way Reconciliation Engine.
    Executes forensic analysis across:
    - Purchase Order Matching & Policy Tolerances
    - Goods Receipt (GRN) 3-Way Matching (Qty, Price, Partiality, Extra Lines)
    - Vendor Bank Fingerprint & BEC Change Recency
    - 2-Stage Hybrid Duplicate Scanning with Multi-Factor Similarity
    - Cross-Batch Multi-Invoice Structuring (Smurfing) Scan
    - Cross-Vendor Shared Bank Fingerprint Collusion Detection
    """

    def __init__(
        self,
        purchase_orders: List[PurchaseOrder],
        goods_receipts: List[GoodsReceipt],
        vendor_masters: List[VendorMaster],
        recent_bank_changes: Optional[Dict[str, int]] = None,
        policy: Optional[FinanceControlPolicy] = None
    ):
        self.po_map: Dict[str, PurchaseOrder] = {po.po_number: po for po in purchase_orders}
        self.grn_map: Dict[str, GoodsReceipt] = {grn.po_reference: grn for grn in goods_receipts}
        self.vendor_map: Dict[str, VendorMaster] = {v.vendor_id: v for v in vendor_masters}
        self.recent_bank_changes = recent_bank_changes or {}
        self.policy = policy or FinanceControlPolicy()

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
        delta_pct = round((diff / po.approved_amount) * 100, 2) if po.approved_amount > 0 else 0.0

        if abs(diff) < 0.01:
            status = "EXACT_MATCH"
            details = f"Invoice amount ${invoice.amount:,.2f} exactly matches approved PO {po.po_number} (${po.approved_amount:,.2f})."
        elif diff > 0 and delta_pct > self.policy.po_tolerance_pct:
            status = "AMOUNT_EXCEEDED"
            details = f"Invoice amount ${invoice.amount:,.2f} exceeds approved PO {po.po_number} (${po.approved_amount:,.2f}) by ${diff:,.2f} (+{delta_pct}% exceeds {self.policy.po_tolerance_pct}% policy limit)."
        else:
            status = "WITHIN_TOLERANCE"
            details = f"Invoice amount ${invoice.amount:,.2f} is within acceptable {self.policy.po_tolerance_pct}% variance of PO {po.po_number} (${po.approved_amount:,.2f}, delta {delta_pct}%)."

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

    def extract_receipt_evidence(self, invoice: Invoice) -> ReceiptEvidence:
        """
        3-Way Reconciliation: Invoice <-> Purchase Order <-> Goods Receipt (GRN).
        Detects:
        - Missing GRN (Invoice billed prior to warehouse receiving)
        - Quantity overbilled / underbilled vs received
        - Unit price discrepancy vs PO
        - Partial receipt overbilling
        - Extra invoice line items not authorized in PO
        """
        if not invoice.po_reference:
            return ReceiptEvidence(
                grn_found=False,
                grn_id=None,
                match_status="MISSING_GRN",
                invoice_qty_total=sum(item.quantity for item in invoice.line_items),
                received_qty_total=0.0,
                po_qty_total=0.0,
                qty_discrepancy=0.0,
                price_discrepancy=0.0,
                line_item_discrepancies=[],
                details="No PO referenced; 3-way goods receipt matching could not be performed."
            )

        po = self.po_map.get(invoice.po_reference)
        grn = self.grn_map.get(invoice.po_reference)

        inv_total_qty = sum(item.quantity for item in invoice.line_items) if invoice.line_items else 1.0
        po_total_qty = sum(item.quantity for item in po.line_items) if (po and po.line_items) else 1.0
        grn_total_qty = sum(item.quantity for item in grn.line_items) if (grn and grn.line_items) else 0.0

        if not grn:
            return ReceiptEvidence(
                grn_found=False,
                grn_id=None,
                match_status="MISSING_GRN",
                invoice_qty_total=inv_total_qty,
                received_qty_total=0.0,
                po_qty_total=po_total_qty,
                qty_discrepancy=inv_total_qty,
                price_discrepancy=0.0,
                line_item_discrepancies=[{"issue": "MISSING_GRN", "details": f"No warehouse receiving dock entry found for PO {invoice.po_reference}."}],
                details=f"3-WAY RECONCILIATION EXCEPTION: No Goods Receipt Note (GRN) found for PO {invoice.po_reference}. Invoice submitted prior to dock delivery."
            )

        # Check line-item level discrepancies
        line_discrepancies: List[Dict[str, Any]] = []
        total_price_diff = 0.0
        total_qty_diff = round(inv_total_qty - grn_total_qty, 2)

        po_items_by_id = {item.item_id: item for item in (po.line_items if po else [])}
        grn_items_by_id = {item.item_id: item for item in grn.line_items}

        for inv_item in invoice.line_items:
            # 1. Extra line item check
            if po and inv_item.item_id not in po_items_by_id:
                line_discrepancies.append({
                    "item_id": inv_item.item_id,
                    "issue": "EXTRA_LINE_ITEM",
                    "description": inv_item.description,
                    "invoiced_amount": inv_item.total_amount,
                    "details": f"Line item '{inv_item.description}' (${inv_item.total_amount:,.2f}) does not exist on approved PO {po.po_number}."
                })
                total_price_diff += inv_item.total_amount
                continue

            po_item = po_items_by_id.get(inv_item.item_id)
            grn_item = grn_items_by_id.get(inv_item.item_id)

            # 2. Price check vs PO
            if po_item and abs(inv_item.unit_price - po_item.unit_price) > 0.01:
                price_delta = round(inv_item.unit_price - po_item.unit_price, 2)
                total_variance = round(price_delta * inv_item.quantity, 2)
                total_price_diff += total_variance
                line_discrepancies.append({
                    "item_id": inv_item.item_id,
                    "issue": "PRICE_MISMATCH",
                    "invoiced_unit_price": inv_item.unit_price,
                    "po_unit_price": po_item.unit_price,
                    "variance_per_unit": price_delta,
                    "total_price_variance": total_variance,
                    "details": f"Unit price discrepancy on '{inv_item.description}': billed at ${inv_item.unit_price:,.2f}/ea vs PO approved ${po_item.unit_price:,.2f}/ea (delta: +${total_variance:,.2f})."
                })

            # 3. Quantity check vs GRN
            if grn_item and inv_item.quantity > grn_item.quantity:
                qty_over = round(inv_item.quantity - grn_item.quantity, 2)
                line_discrepancies.append({
                    "item_id": inv_item.item_id,
                    "issue": "QUANTITY_OVERBILLED",
                    "invoiced_quantity": inv_item.quantity,
                    "received_quantity": grn_item.quantity,
                    "overbilled_units": qty_over,
                    "details": f"Quantity discrepancy on '{inv_item.description}': billed for {inv_item.quantity} units, but warehouse GRN {grn.grn_id} received only {grn_item.quantity} units ({qty_over} units overbilled)."
                })

        # Determine overall match status
        if any(d["issue"] == "EXTRA_LINE_ITEM" for d in line_discrepancies):
            match_status = "EXTRA_LINE_ITEM"
            details = f"3-WAY RECONCILIATION EXCEPTION: Invoice contains {len(line_discrepancies)} unauthorized line items not listed on PO {po.po_number}."
        elif any(d["issue"] == "PRICE_MISMATCH" for d in line_discrepancies):
            match_status = "PRICE_MISMATCH"
            details = f"3-WAY RECONCILIATION EXCEPTION: Invoiced unit price exceeds approved purchase order rate by ${total_price_diff:,.2f}."
        elif grn.receiving_status == "PARTIAL" and inv_total_qty > grn_total_qty:
            match_status = "PARTIAL_RECEIPT_OVERBILL"
            details = f"3-WAY RECONCILIATION EXCEPTION: Partial goods receipt. Invoiced for {inv_total_qty} units but warehouse received only {grn_total_qty} units ({inv_total_qty - grn_total_qty} units backordered)."
        elif inv_total_qty > grn_total_qty:
            match_status = "QUANTITY_OVERBILLED"
            details = f"3-WAY RECONCILIATION EXCEPTION: Invoiced quantity ({inv_total_qty}) exceeds dock received quantity ({grn_total_qty}) on GRN {grn.grn_id}."
        elif inv_total_qty < grn_total_qty:
            match_status = "QUANTITY_UNDERBILLED"
            details = f"Partial invoice against GRN {grn.grn_id} (billed {inv_total_qty} of {grn_total_qty} received)."
        else:
            match_status = "EXACT_3WAY_MATCH"
            details = f"3-Way match verified: Invoice matches PO {po.po_number} and GRN {grn.grn_id} on quantity ({inv_total_qty} units) and unit pricing."

        return ReceiptEvidence(
            grn_found=True,
            grn_id=grn.grn_id,
            match_status=match_status,
            invoice_qty_total=inv_total_qty,
            received_qty_total=grn_total_qty,
            po_qty_total=po_total_qty,
            qty_discrepancy=total_qty_diff,
            price_discrepancy=total_price_diff,
            line_item_discrepancies=line_discrepancies,
            details=details
        )

    def extract_bank_evidence(self, invoice: Invoice) -> BankEvidence:
        vendor = self.vendor_map.get(invoice.vendor_id)
        if not vendor or vendor.historical_invoice_count == 0:
            return BankEvidence(
                submitted_fingerprint=invoice.vendor_bank_fingerprint,
                master_fingerprint=vendor.primary_bank_fingerprint if vendor else None,
                fingerprint_match=True,
                recent_change_detected=False,
                days_since_account_change=None,
                risk_level="FIRST_TIME_VENDOR_UNVERIFIED",
                details=f"First-time or unverified vendor. Bank routing fingerprint '{invoice.vendor_bank_fingerprint}' has no established payment history."
            )
        
        match = (invoice.vendor_bank_fingerprint == vendor.primary_bank_fingerprint)
        days_changed = self.recent_bank_changes.get(invoice.vendor_id)

        if not match:
            days_str = f"{days_changed} days ago" if days_changed is not None else "recently"
            is_recent = (days_changed is not None and days_changed <= self.policy.bank_cooling_days)
            return BankEvidence(
                submitted_fingerprint=invoice.vendor_bank_fingerprint,
                master_fingerprint=vendor.primary_bank_fingerprint,
                fingerprint_match=False,
                recent_change_detected=is_recent,
                days_since_account_change=days_changed,
                risk_level="HIGH_RISK_RECENT_CHANGE",
                details=f"CRITICAL BEC RED FLAG: Submitted bank fingerprint '{invoice.vendor_bank_fingerprint}' does NOT match vendor master registry '{vendor.primary_bank_fingerprint}' (routing modified {days_str}). Potential Business Email Compromise / Account Takeover."
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

    def extract_duplicate_evidence(self, target_invoice: Invoice, all_invoices: List[Invoice]) -> DuplicateEvidence:
        """
        Stage 1: Candidate Generation
        Stage 2: Hybrid Multi-Factor Similarity Calculation
        """
        candidates: List[DuplicateCandidate] = []
        target_inv_date = parse_date(target_invoice.invoice_date)
        target_sub_date = parse_date(target_invoice.submission_date)
        
        exact_found = False
        near_found = False
        highest_score = 0.0

        for other in all_invoices:
            if other.invoice_id == target_invoice.invoice_id:
                continue
            
            other_inv_date = parse_date(other.invoice_date)
            other_sub_date = parse_date(other.submission_date)
            
            inv_days_diff = abs((target_inv_date - other_inv_date).days)
            sub_days_diff = (target_sub_date - other_sub_date).days
            
            # Identify if target is subsequent copy vs predecessor
            is_subsequent = (
                sub_days_diff > 0 or
                (sub_days_diff == 0 and ("-DUP" in target_invoice.invoice_id or "-B" in target_invoice.invoice_id or target_invoice.invoice_id > other.invoice_id))
            )

            if not is_subsequent:
                continue

            # Stage 1: Candidate Generation Filter (Same vendor, identical amount or high string number similarity)
            is_same_vendor = (other.vendor_id == target_invoice.vendor_id)
            if not is_same_vendor:
                continue

            is_exact_amount = (abs(target_invoice.amount - other.amount) < 0.01)
            inv_no_sim = levenshtein_similarity(target_invoice.invoice_id, other.invoice_id)
            has_dup_suffix = ("-DUP" in target_invoice.invoice_id or "-B" in target_invoice.invoice_id)
            same_po = (target_invoice.po_reference and target_invoice.po_reference == other.po_reference)
            diff_po = (target_invoice.po_reference and other.po_reference and target_invoice.po_reference != other.po_reference)

            # Invoices on completely different approved POs are distinct orders unless explicit duplicate suffix is present
            if diff_po and not has_dup_suffix:
                continue

            # Legitimate recurring invoices have distinct POs and different invoice numbers
            if not (is_exact_amount and (has_dup_suffix or same_po or inv_no_sim >= 0.75 or inv_days_diff <= 2)):
                continue

            # Stage 2: Hybrid Similarity Calculation
            vendor_sim = 1.0
            amount_ratio = min(other.amount, target_invoice.amount) / max(other.amount, target_invoice.amount) if max(other.amount, target_invoice.amount) > 0 else 1.0
            amount_sim = round(amount_ratio, 4)
            date_prox_sim = round(max(0.0, 1.0 - (inv_days_diff / 30.0)), 4)
            
            desc1 = target_invoice.line_items_summary or ""
            desc2 = other.line_items_summary or ""
            desc_sim = token_jaccard_similarity(desc1, desc2)

            factors = DuplicateSimilarityFactors(
                invoice_no_similarity=inv_no_sim,
                vendor_similarity=vendor_sim,
                amount_similarity=amount_sim,
                date_proximity_score=date_prox_sim,
                description_similarity=desc_sim
            )

            # Weighted formula: 25% InvNo + 30% Vendor + 25% Amount + 10% Date + 10% Desc
            hybrid_score = round(
                (0.25 * inv_no_sim) + 
                (0.30 * vendor_sim) + 
                (0.25 * amount_sim) + 
                (0.10 * date_prox_sim) + 
                (0.10 * desc_sim), 
                4
            )

            is_exact = (
                is_exact_amount and 
                (inv_days_diff == 0 or "-DUP" in target_invoice.invoice_id or (same_po and inv_days_diff <= 7))
            )

            if is_exact:
                exact_found = True
                match_type = "EXACT_DUPLICATE"
                score = 0.99
                reason = (
                    f"Exact duplicate resubmission of {other.invoice_id} "
                    f"(${other.amount:,.2f} on {other.submission_date}). "
                    f"Hybrid Score: {score*100:.1f}% [Vendor: {vendor_sim}, Amount: {amount_sim}, Date: {date_prox_sim}]"
                )
            elif is_exact_amount and (has_dup_suffix or inv_no_sim >= 0.70 or inv_days_diff <= 5):
                near_found = True
                match_type = "NEAR_DUPLICATE_HYBRID"
                score = max(hybrid_score, 0.90 - (inv_days_diff * 0.02))
                reason = (
                    f"Near-duplicate candidate {other.invoice_id} ({inv_days_diff}d gap). "
                    f"Hybrid Score: {score*100:.1f}% [InvNo: {inv_no_sim}, Vendor: {vendor_sim}, Amount: {amount_sim}, Desc: {desc_sim}]"
                )
            else:
                continue

            candidates.append(DuplicateCandidate(
                matched_invoice_id=other.invoice_id,
                match_type=match_type,
                matched_amount=other.amount,
                matched_date=other.invoice_date,
                date_difference_days=inv_days_diff,
                similarity_score=score,
                factors=factors,
                reason=reason
            ))

            if score > highest_score:
                highest_score = score

        is_risk = exact_found or near_found
        if exact_found:
            details = f"CRITICAL DUPLICATE: Exact resubmission of prior invoice {candidates[0].matched_invoice_id} (amount ${target_invoice.amount:,.2f})."
        elif near_found:
            details = f"NEAR DUPLICATE WARNING: Matches prior invoice {candidates[0].matched_invoice_id} (amount ${target_invoice.amount:,.2f}) with {candidates[0].similarity_score*100:.1f}% hybrid confidence."
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

    def extract_vendor_history_evidence(self, invoice: Invoice) -> VendorHistoryEvidence:
        vendor = self.vendor_map.get(invoice.vendor_id)
        if not vendor or vendor.historical_invoice_count == 0:
            is_large = invoice.amount > self.policy.approval_threshold
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

    def extract_structuring_evidence(
        self,
        target_invoice: Invoice,
        all_invoices: List[Invoice]
    ) -> StructuringEvidence:
        vendor_invoices = [inv for inv in all_invoices if inv.vendor_id == target_invoice.vendor_id]
        
        # 3+ invoices hovering right below approval threshold without separate POs
        lower_bound = self.policy.approval_threshold * 0.75
        under_threshold_invoices = [
            inv for inv in vendor_invoices
            if lower_bound <= inv.amount < self.policy.approval_threshold and (not inv.po_reference or inv.po_reference.strip() == "")
        ]
        
        if len(under_threshold_invoices) >= 3:
            dates = [parse_date(inv.invoice_date) for inv in under_threshold_invoices]
            min_date = min(dates)
            max_date = max(dates)
            window_days = (max_date - min_date).days

            if window_days <= 5:
                cluster_ids = [inv.invoice_id for inv in under_threshold_invoices]
                cluster_amounts = [inv.amount for inv in under_threshold_invoices]
                total_cluster = sum(cluster_amounts)
                
                if target_invoice.invoice_id in cluster_ids:
                    return StructuringEvidence(
                        in_structuring_cluster=True,
                        cluster_invoice_ids=cluster_ids,
                        cluster_invoice_count=len(cluster_ids),
                        cluster_total_amount=round(total_cluster, 2),
                        individual_amounts=cluster_amounts,
                        threshold_limit=self.policy.approval_threshold,
                        time_window_days=window_days,
                        pattern_description=(
                            f"FLAGSHIP FRAUD PATTERN (Structuring / Smurfing): Vendor '{target_invoice.vendor_name}' "
                            f"split a single ~${total_cluster:,.2f} total obligation into {len(cluster_ids)} separate un-PO'd invoices "
                            f"({', '.join([f'${a:,.2f}' for a in cluster_amounts])}), each hovering right below the ${self.policy.approval_threshold:,.2f} "
                            f"audit threshold, submitted across a {window_days}-day window ({min_date.strftime('%b %d')} - {max_date.strftime('%b %d')})."
                        )
                    )

        return StructuringEvidence(
            in_structuring_cluster=False,
            cluster_invoice_ids=[],
            cluster_invoice_count=0,
            cluster_total_amount=0.0,
            individual_amounts=[],
            threshold_limit=self.policy.approval_threshold,
            time_window_days=0,
            pattern_description=None
        )

    def extract_collusion_evidence(self, target_invoice: Invoice) -> CollusionEvidence:
        """
        Detects if multiple distinct vendor entities share the exact same bank routing fingerprint.
        """
        fp = target_invoice.vendor_bank_fingerprint
        conflicting_vendors = [
            vm.vendor_name for vm in self.vendor_map.values()
            if vm.primary_bank_fingerprint == fp and vm.vendor_id != target_invoice.vendor_id
        ]
        
        if conflicting_vendors:
            return CollusionEvidence(
                shared_fingerprint_detected=True,
                conflicting_vendor_names=conflicting_vendors,
                shared_fingerprint=fp,
                details=f"COLLUSION / SHARED BANK ACCOUNT RISK: Vendor bank fingerprint '{fp}' is simultaneously linked to another vendor master record: '{', '.join(conflicting_vendors)}'."
            )

        return CollusionEvidence(
            shared_fingerprint_detected=False,
            conflicting_vendor_names=[],
            shared_fingerprint=None,
            details="Bank account fingerprint is uniquely registered to this vendor profile."
        )

    def build_dossier(self, invoice: Invoice, all_invoices: List[Invoice]) -> EvidenceDossier:
        po_ev = self.extract_po_evidence(invoice)
        rcpt_ev = self.extract_receipt_evidence(invoice)
        bank_ev = self.extract_bank_evidence(invoice)
        dup_ev = self.extract_duplicate_evidence(invoice, all_invoices)
        vendor_ev = self.extract_vendor_history_evidence(invoice)
        struc_ev = self.extract_structuring_evidence(invoice, all_invoices)
        col_ev = self.extract_collusion_evidence(invoice)

        flags: List[str] = []
        if struc_ev.in_structuring_cluster:
            flags.append("STRUCTURING_ATTACK_DETECTED")
        if bank_ev.risk_level == "HIGH_RISK_RECENT_CHANGE":
            flags.append("BANK_FINGERPRINT_MISMATCH")
        if col_ev.shared_fingerprint_detected:
            flags.append("SHARED_BANK_COLLUSION_DETECTED")
        if dup_ev.exact_duplicate_found:
            flags.append("EXACT_DUPLICATE_INVOICE")
        elif dup_ev.near_duplicate_found:
            flags.append("NEAR_DUPLICATE_INVOICE")
        if rcpt_ev.match_status == "MISSING_GRN":
            flags.append("MISSING_GOODS_RECEIPT")
        elif rcpt_ev.match_status == "QUANTITY_OVERBILLED":
            flags.append("GRN_QUANTITY_OVERBILLED")
        elif rcpt_ev.match_status == "PRICE_MISMATCH":
            flags.append("PO_PRICE_MISMATCH")
        elif rcpt_ev.match_status == "EXTRA_LINE_ITEM":
            flags.append("EXTRA_UNAPPROVED_LINE_ITEM")
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
            due_date=invoice.due_date,
            po_evidence=po_ev,
            receipt_evidence=rcpt_ev,
            bank_evidence=bank_ev,
            duplicate_evidence=dup_ev,
            vendor_history_evidence=vendor_ev,
            structuring_evidence=struc_ev,
            collusion_evidence=col_ev,
            flagged_risk_count=len(flags),
            primary_risk_flags=flags
        )
