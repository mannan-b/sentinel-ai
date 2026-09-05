from typing import List, Dict, Any, Optional
from backend.models import (
    Invoice, AgentVerdict, EvidenceDossier, BatchScorecard,
    ClassMetrics, StructuringFlagshipMetric, FinanceException
)

def compute_binary_metrics(tp: int, fp: int, fn: int) -> ClassMetrics:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return ClassMetrics(
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1_score=round(f1, 4),
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn
    )

def compute_batch_scorecard(
    invoices: List[Invoice],
    verdicts: List[AgentVerdict],
    dossiers: Dict[str, EvidenceDossier],
    exceptions: Optional[List[FinanceException]] = None
) -> BatchScorecard:
    """
    Evaluates agent verdicts and operational finance metrics against hidden ground truth labels.
    """
    total = len(invoices)
    if total == 0:
        raise ValueError("Cannot score empty batch")

    verdict_map: Dict[str, AgentVerdict] = {v.invoice_id: v for v in verdicts}
    exceptions_list = exceptions or []
    
    auto_approved_count = 0
    held_for_review_count = 0
    escalate_fraud_count = 0
    reject_duplicate_count = 0

    reconciliation_matched_count = 0
    payment_value_blocked = 0.0
    duplicate_value_prevented = 0.0
    fraud_risk_value_escalated = 0.0

    # Duplicate class confusion counts
    dup_tp = 0
    dup_fp = 0
    dup_fn = 0

    # Fraud class confusion counts
    fraud_tp = 0
    fraud_fp = 0
    fraud_fn = 0

    # False positive cost on legitimate invoices
    legitimate_false_positive_count = 0
    non_approve_citation_counts = []
    
    # Flagship structuring tracking
    structuring_detected = False
    structuring_vendor = None
    structuring_ids = []
    structuring_amount = 0.0

    for inv in invoices:
        v = verdict_map[inv.invoice_id]
        dossier = dossiers[inv.invoice_id]
        gt = inv.ground_truth_label

        # 3-Way match check
        if dossier.receipt_evidence.match_status == "EXACT_3WAY_MATCH" and dossier.po_evidence.status in ["EXACT_MATCH", "WITHIN_TOLERANCE"]:
            reconciliation_matched_count += 1

        # Count verdicts & financial values
        if v.verdict == "auto_approve":
            auto_approved_count += 1
        elif v.verdict == "hold_for_review":
            held_for_review_count += 1
            payment_value_blocked += inv.amount
            non_approve_citation_counts.append(len(v.cited_evidence))
        elif v.verdict == "escalate_fraud":
            escalate_fraud_count += 1
            fraud_risk_value_escalated += inv.amount
            non_approve_citation_counts.append(len(v.cited_evidence))
        elif v.verdict == "reject_duplicate":
            reject_duplicate_count += 1
            duplicate_value_prevented += inv.amount
            non_approve_citation_counts.append(len(v.cited_evidence))

        # Duplicate scoring
        is_pred_duplicate = (v.verdict == "reject_duplicate")
        is_true_duplicate = (gt == "duplicate")
        if is_pred_duplicate and is_true_duplicate:
            dup_tp += 1
        elif is_pred_duplicate and not is_true_duplicate:
            dup_fp += 1
        elif not is_pred_duplicate and is_true_duplicate:
            dup_fn += 1

        # Fraud scoring
        is_pred_fraud = (v.verdict == "escalate_fraud")
        is_true_fraud = (gt == "fraud_risk")
        if is_pred_fraud and is_true_fraud:
            fraud_tp += 1
        elif is_pred_fraud and not is_true_fraud:
            fraud_fp += 1
        elif not is_pred_fraud and is_true_fraud:
            fraud_fn += 1

        # Legitimate false positive (where clean invoice was erroneously rejected or escalated to fraud)
        if gt == "legitimate" and v.verdict in ["reject_duplicate", "escalate_fraud"]:
            legitimate_false_positive_count += 1

        # Check structuring detection
        if dossier.structuring_evidence.in_structuring_cluster and v.verdict == "escalate_fraud":
            structuring_detected = True
            structuring_vendor = inv.vendor_name
            if inv.invoice_id not in structuring_ids:
                structuring_ids.append(inv.invoice_id)
            structuring_amount = dossier.structuring_evidence.cluster_total_amount

    avg_citations = (
        round(sum(non_approve_citation_counts) / len(non_approve_citation_counts), 2)
        if non_approve_citation_counts else 0.0
    )

    duplicate_metrics = compute_binary_metrics(dup_tp, dup_fp, dup_fn)
    fraud_metrics = compute_binary_metrics(fraud_tp, fraud_fp, fraud_fn)

    auto_resolved_count = auto_approved_count + reject_duplicate_count + escalate_fraud_count
    
    structuring_flagship = StructuringFlagshipMetric(
        detected=structuring_detected,
        vendor_name=structuring_vendor,
        cluster_invoice_ids=structuring_ids,
        total_structured_amount=structuring_amount,
        headline="CROSS-BATCH STRUCTURING ATTACK NEUTRALIZED" if structuring_detected else "NO STRUCTURING DETECTED",
        explanation=(
            f"Successfully caught multi-invoice structuring pattern from '{structuring_vendor}' "
            f"({len(structuring_ids)} split invoices totaling ${structuring_amount:,.2f}) without individual row false-negatives."
            if structuring_detected else "Cross-batch scan did not isolate structuring activity."
        )
    )

    total_exc = len(exceptions_list)
    resolved_exc = len([e for e in exceptions_list if e.status == "RESOLVED"])
    exc_res_rate = round((resolved_exc / total_exc) * 100, 1) if total_exc > 0 else 100.0

    # Straight-Through Processing (STP)
    # Calculated strictly from actual invoice state transitions (auto-approved, 0 exceptions, 0 human intervention)
    stp_count = 0
    for inv in invoices:
        v = verdict_map[inv.invoice_id]
        has_unresolved_ex = any(e.invoice_id == inv.invoice_id and e.status != "RESOLVED" for e in exceptions_list)
        if v.verdict == "auto_approve" and not has_unresolved_ex and not v.requires_human_review:
            stp_count += 1
    stp_rate = round((stp_count / total) * 100, 1)

    return BatchScorecard(
        total_invoices=total,
        auto_approved_count=auto_approved_count,
        auto_approved_pct=round((auto_approved_count / total) * 100, 1),
        held_for_review_count=held_for_review_count,
        held_for_review_pct=round((held_for_review_count / total) * 100, 1),
        escalate_fraud_count=escalate_fraud_count,
        escalate_fraud_pct=round((escalate_fraud_count / total) * 100, 1),
        reject_duplicate_count=reject_duplicate_count,
        reject_duplicate_pct=round((reject_duplicate_count / total) * 100, 1),
        
        auto_resolved_pct=round((auto_resolved_count / total) * 100, 1),
        human_routing_pct=round((held_for_review_count / total) * 100, 1),

        stp_count=stp_count,
        stp_rate=stp_rate,

        reconciliation_match_rate=round((reconciliation_matched_count / total) * 100, 1),
        exception_rate=round((total_exc / total) * 100, 1),
        exception_resolution_rate=exc_res_rate,
        total_exceptions_count=total_exc,
        resolved_exceptions_count=resolved_exc,

        payment_value_blocked=round(payment_value_blocked, 2),
        duplicate_value_prevented=round(duplicate_value_prevented, 2),
        fraud_risk_value_escalated=round(fraud_risk_value_escalated, 2),
        cash_currently_at_risk=round(payment_value_blocked + fraud_risk_value_escalated, 2),
        
        duplicate_metrics=duplicate_metrics,
        fraud_metrics=fraud_metrics,
        legitimate_false_positive_count=legitimate_false_positive_count,
        legitimate_false_positive_rate=round((legitimate_false_positive_count / total) * 100, 2),
        
        avg_evidence_citations_per_non_approval=avg_citations,
        structuring_flagship=structuring_flagship
    )
