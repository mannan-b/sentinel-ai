from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime

GroundTruthLabel = Literal["legitimate", "duplicate", "fraud_risk", "needs_review"]
VerdictType = Literal["auto_approve", "hold_for_review", "escalate_fraud", "reject_duplicate"]
PaymentStatus = Literal[
    "READY_FOR_PAYMENT", 
    "PAYMENT_ELIGIBLE",
    "RELEASED",
    "AWAITING_REVIEW", 
    "PAYMENT_HOLD",
    "FRAUD_HOLD", 
    "DUPLICATE_REJECTED", 
    "MISSING_DOCUMENTATION", 
    "BLOCKED_BY_RECONCILIATION", 
    "PAID", 
    "CANCELLED"
]
ApprovalStatus = Literal["PENDING", "APPROVED", "AUTO_APPROVED", "HELD", "REJECTED", "ESCALATED", "RESOLVED", "RELEASED"]
ExceptionSeverity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
ExceptionStatus = Literal["OPEN", "AI_RECOMMENDED", "HUMAN_REVIEW", "RESOLVED", "ESCALATED"]
ExceptionOwner = Literal["AP_CLERK", "PROCUREMENT_BUYER", "CONTROLLER", "INTERNAL_AUDIT", "TREASURY"]
ControlStatus = Literal["PENDING", "VERIFIED", "FAILED"]

class LineItem(BaseModel):
    item_id: str
    description: str
    quantity: float
    unit_price: float
    total_amount: float
    unit_of_measure: str = "EA"

class GoodsReceipt(BaseModel):
    grn_id: str
    po_reference: str
    vendor_id: str
    vendor_name: str
    received_date: str
    line_items: List[LineItem] = Field(default_factory=list)
    receiving_status: Literal["FULL", "PARTIAL", "DAMAGED", "REJECTED"] = "FULL"
    receiver_name: str = "Warehouse Team"
    notes: Optional[str] = "Goods received and inspected at dock"

class PurchaseOrder(BaseModel):
    po_number: str
    vendor_id: str
    vendor_name: str
    approved_amount: float
    description: str
    created_date: str
    line_items: List[LineItem] = Field(default_factory=list)
    payment_terms: str = "NET30"
    department: str = "Operations & IT"
    is_active: bool = True

class VendorMaster(BaseModel):
    vendor_id: str
    vendor_name: str
    primary_bank_fingerprint: str
    established_date: str
    historical_invoice_count: int
    historical_avg_amount: float
    is_trusted: bool = True
    default_payment_terms: str = "NET30"
    vendor_category: str = "General Services"

class Invoice(BaseModel):
    invoice_id: str
    vendor_name: str
    vendor_id: str
    amount: float
    po_reference: Optional[str] = None
    vendor_bank_fingerprint: str
    invoice_date: str
    submission_date: str
    due_date: str
    payment_terms: str = "NET30"
    line_items_summary: Optional[str] = "General services & operational supplies"
    line_items: List[LineItem] = Field(default_factory=list)
    payment_status: PaymentStatus = "AWAITING_REVIEW"
    approval_status: ApprovalStatus = "PENDING"
    # Hidden ground truth used strictly for scoring/evaluation (never passed to agent/LLM)
    ground_truth_label: GroundTruthLabel
    ground_truth_reason: Optional[str] = None

class POEvidence(BaseModel):
    po_referenced: bool
    po_found: bool
    po_number: Optional[str] = None
    po_approved_amount: Optional[float] = None
    amount_difference: Optional[float] = None
    amount_delta_pct: Optional[float] = None
    status: Literal["EXACT_MATCH", "WITHIN_TOLERANCE", "AMOUNT_EXCEEDED", "NO_PO_REFERENCED", "INVALID_PO_REFERENCE"]
    details: str

class ReceiptEvidence(BaseModel):
    grn_found: bool
    grn_id: Optional[str] = None
    match_status: Literal[
        "EXACT_3WAY_MATCH", 
        "MISSING_GRN", 
        "QUANTITY_OVERBILLED", 
        "QUANTITY_UNDERBILLED", 
        "PARTIAL_RECEIPT_OVERBILL", 
        "PRICE_MISMATCH", 
        "EXTRA_LINE_ITEM", 
        "MULTIPLE_INVOICES_EXCEEDED_PO_LINE", 
        "DAMAGED_GOODS_RECEIPT"
    ]
    invoice_qty_total: float = 0.0
    received_qty_total: float = 0.0
    po_qty_total: float = 0.0
    qty_discrepancy: float = 0.0
    price_discrepancy: float = 0.0
    line_item_discrepancies: List[Dict[str, Any]] = Field(default_factory=list)
    details: str

class BankEvidence(BaseModel):
    submitted_fingerprint: str
    master_fingerprint: Optional[str] = None
    fingerprint_match: bool
    recent_change_detected: bool
    days_since_account_change: Optional[int] = None
    risk_level: Literal["NORMAL", "HIGH_RISK_RECENT_CHANGE", "FIRST_TIME_VENDOR_UNVERIFIED"]
    details: str

class DuplicateSimilarityFactors(BaseModel):
    invoice_no_similarity: float
    vendor_similarity: float
    amount_similarity: float
    date_proximity_score: float
    description_similarity: float

class DuplicateCandidate(BaseModel):
    matched_invoice_id: str
    match_type: Literal["EXACT_DUPLICATE", "NEAR_DUPLICATE_HYBRID", "NEAR_DUPLICATE_WINDOW"]
    matched_amount: float
    matched_date: str
    date_difference_days: int
    similarity_score: float
    factors: Optional[DuplicateSimilarityFactors] = None
    reason: str

class DuplicateEvidence(BaseModel):
    is_duplicate_risk: bool
    exact_duplicate_found: bool
    near_duplicate_found: bool
    duplicate_score: float
    candidates: List[DuplicateCandidate] = Field(default_factory=list)
    details: str

class VendorHistoryEvidence(BaseModel):
    is_first_time_vendor: bool
    historical_invoice_count: int
    historical_avg_amount: float
    amount_vs_history_ratio: float
    is_unusually_large_first_time: bool
    vendor_risk_tier: Literal["LOW_ESTABLISHED", "MODERATE", "HIGH_FIRST_TIME_LARGE"]
    details: str

class StructuringEvidence(BaseModel):
    in_structuring_cluster: bool
    cluster_invoice_ids: List[str] = Field(default_factory=list)
    cluster_invoice_count: int = 0
    cluster_total_amount: float = 0.0
    individual_amounts: List[float] = Field(default_factory=list)
    threshold_limit: float = 10000.0
    time_window_days: int = 0
    pattern_description: Optional[str] = None

class CollusionEvidence(BaseModel):
    shared_fingerprint_detected: bool = False
    conflicting_vendor_names: List[str] = Field(default_factory=list)
    shared_fingerprint: Optional[str] = None
    details: str = "No cross-vendor shared bank account detected."

class EvidenceDossier(BaseModel):
    invoice_id: str
    vendor_name: str
    amount: float
    invoice_date: str
    submission_date: str
    due_date: str
    po_evidence: POEvidence
    receipt_evidence: ReceiptEvidence
    bank_evidence: BankEvidence
    duplicate_evidence: DuplicateEvidence
    vendor_history_evidence: VendorHistoryEvidence
    structuring_evidence: StructuringEvidence
    collusion_evidence: CollusionEvidence
    flagged_risk_count: int
    primary_risk_flags: List[str] = Field(default_factory=list)

class CitedEvidenceItem(BaseModel):
    field_path: str
    observed_value: Any
    significance: str

class AgentVerdict(BaseModel):
    invoice_id: str
    verdict: VerdictType
    confidence: float
    cited_evidence: List[CitedEvidenceItem] = Field(default_factory=list)
    primary_reason: str
    recommended_action: str
    next_best_action: str
    requires_human_review: bool
    dossier_summary: Optional[Dict[str, Any]] = None
    processed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class FinanceControlPolicy(BaseModel):
    po_tolerance_pct: float = 5.0
    grn_tolerance_pct: float = 0.0
    approval_threshold: float = 10000.0
    duplicate_similarity_threshold: float = 0.85
    bank_cooling_days: int = 30
    high_risk_amount_threshold: float = 25000.0
    auto_approve_clean_3way: bool = True

class FinanceException(BaseModel):
    exception_id: str
    invoice_id: str
    vendor_name: str
    vendor_id: str
    invoice_amount: float
    exception_type: Literal[
        "MISSING_GRN", 
        "QUANTITY_MISMATCH", 
        "PRICE_MISMATCH", 
        "EXTRA_LINE_ITEM", 
        "DUPLICATE_INVOICE", 
        "BANK_CHANGE_RISK", 
        "STRUCTURING_ATTACK", 
        "PO_VARIANCE", 
        "COLLUSION_RISK", 
        "FIRST_TIME_LARGE_BILL"
    ]
    severity: ExceptionSeverity
    priority_score: float # 0 to 100
    financial_impact: float
    affected_records: List[str] = Field(default_factory=list)
    evidence_summary: str
    recommended_action: str
    suggested_owner: ExceptionOwner
    status: ExceptionStatus = "OPEN"
    created_at: str
    resolution_deadline: str
    historical_precedent: Optional[Dict[str, Any]] = None
    resolution_notes: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[str] = None

class ExceptionGroup(BaseModel):
    group_id: str
    title: str
    vendor_name: str
    vendor_id: str
    exception_type: str
    invoice_count: int
    total_financial_impact: float
    invoice_ids: List[str] = Field(default_factory=list)
    recommended_bulk_action: str
    severity: ExceptionSeverity
    pattern_summary: str

class BankChangeAlert(BaseModel):
    vendor_id: str
    vendor_name: str
    old_fingerprint: str
    new_fingerprint: str
    days_since_change: int
    affected_invoice_ids: List[str] = Field(default_factory=list)
    affected_payment_value: float = 0.0
    risk_severity: ExceptionSeverity = "CRITICAL"
    independent_phone_verified: ControlStatus = "PENDING"
    cfo_signoff: ControlStatus = "PENDING"
    account_ownership_verified: ControlStatus = "PENDING"
    cooling_period_elapsed: ControlStatus = "PENDING"
    all_controls_satisfied: bool = False

class CashOutflowBucket(BaseModel):
    days_range: str
    label: str
    approved_amount: float
    held_amount: float
    high_risk_amount: float
    total_projected_outflow: float

class CashPositionSummary(BaseModel):
    total_approved_payable: float
    total_held_payable: float
    total_fraud_risk_payable: float
    total_duplicate_prevented: float
    overdue_payable: float
    payable_due_7d: float
    payable_due_14d: float
    payable_due_30d: float
    cash_at_risk: float
    outflow_forecast: List[CashOutflowBucket] = Field(default_factory=list)

class AuditEvent(BaseModel):
    event_id: str
    timestamp: str
    action: str
    actor: str
    affected_record: str
    previous_state: Optional[str] = None
    new_state: str
    reason: str
    event_hash: str = ""
    previous_hash: str = ""

class PaymentReleaseEvaluation(BaseModel):
    invoice_id: str
    permitted: bool
    payment_status: PaymentStatus
    approval_status: ApprovalStatus
    blocking_reasons: List[str] = Field(default_factory=list)
    satisfied_controls: List[str] = Field(default_factory=list)
    pending_controls: List[str] = Field(default_factory=list)
    evaluation_timestamp: str

class WhyExplanation(BaseModel):
    invoice_id: str
    summary: str
    is_payment_blocked: bool
    payment_status: str
    payment_block_reasons: List[str] = Field(default_factory=list)
    reconciliation_findings: List[str] = Field(default_factory=list)
    duplicate_findings: List[str] = Field(default_factory=list)
    fraud_risk_findings: List[str] = Field(default_factory=list)
    cash_at_risk_amount: float = 0.0
    recommended_action: str
    action_owner: str

class ClassMetrics(BaseModel):
    precision: float
    recall: float
    f1_score: float
    true_positives: int
    false_positives: int
    false_negatives: int

class StructuringFlagshipMetric(BaseModel):
    detected: bool
    vendor_name: Optional[str] = None
    cluster_invoice_ids: List[str] = Field(default_factory=list)
    total_structured_amount: float = 0.0
    headline: str
    explanation: str

class BatchScorecard(BaseModel):
    total_invoices: int
    auto_approved_count: int
    auto_approved_pct: float
    held_for_review_count: int
    held_for_review_pct: float
    escalate_fraud_count: int
    escalate_fraud_pct: float
    reject_duplicate_count: int
    reject_duplicate_pct: float
    
    auto_resolved_pct: float
    human_routing_pct: float
    
    # Straight-Through Processing (STP)
    stp_count: int = 0
    stp_rate: float = 0.0
    
    # 3-Way Reconciliation & Operational Metrics
    reconciliation_match_rate: float
    exception_rate: float
    exception_resolution_rate: float
    total_exceptions_count: int
    resolved_exceptions_count: int
    
    # Financial Control Impact
    payment_value_blocked: float
    duplicate_value_prevented: float
    fraud_risk_value_escalated: float
    cash_currently_at_risk: float
    
    duplicate_metrics: ClassMetrics
    fraud_metrics: ClassMetrics
    legitimate_false_positive_count: int
    legitimate_false_positive_rate: float
    
    avg_evidence_citations_per_non_approval: float
    structuring_flagship: StructuringFlagshipMetric
