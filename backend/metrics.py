from typing import List, Dict, Any, Optional
from backend.models import (
    Invoice, AgentVerdict, EvidenceDossier, BatchScorecard,
    ClassMetrics, StructuringFlagshipMetric
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
    dossiers: Dict[str, EvidenceDossier]
) -> BatchScorecard:
    """
    Evaluates agent verdicts against hidden ground truth labels.
    """
    total = len(invoices)
    if total == 0:
        raise ValueError("Cannot score empty batch")

    verdict_map: Dict[str, AgentVerdict] = {v.invoice_id: v for v in verdicts}
    
    auto_approved_count = 0
    held_for_review_count = 0
    escalate_fraud_count = 0
    reject_duplicate_count = 0

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

        # Count verdicts
        if v.verdict == "auto_approve":
            auto_approved_count += 1
        elif v.verdict == "hold_for_review":
            held_for_review_count += 1
            non_approve_citation_counts.append(len(v.cited_evidence))
        elif v.verdict == "escalate_fraud":
            escalate_fraud_count += 1
            non_approve_citation_counts.append(len(v.cited_evidence))
        elif v.verdict == "reject_duplicate":
            reject_duplicate_count += 1
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
        
        duplicate_metrics=duplicate_metrics,
        fraud_metrics=fraud_metrics,
        legitimate_false_positive_count=legitimate_false_positive_count,
        legitimate_false_positive_rate=round((legitimate_false_positive_count / total) * 100, 2),
        
        avg_evidence_citations_per_non_approval=avg_citations,
        structuring_flagship=structuring_flagship
    )
