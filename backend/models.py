from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import date, datetime

GroundTruthLabel = Literal["legitimate", "duplicate", "fraud_risk", "needs_review"]
VerdictType = Literal["auto_approve", "hold_for_review", "escalate_fraud", "reject_duplicate"]

class PurchaseOrder(BaseModel):
    po_number: str
    vendor_id: str
    vendor_name: str
    approved_amount: float
    description: str
    created_date: str
    is_active: bool = True

class VendorMaster(BaseModel):
    vendor_id: str
    vendor_name: str
    primary_bank_fingerprint: str
    established_date: str
    historical_invoice_count: int
    historical_avg_amount: float
    is_trusted: bool = True

class Invoice(BaseModel):
    invoice_id: str
    vendor_name: str
    vendor_id: str
    amount: float
    po_reference: Optional[str] = None
    vendor_bank_fingerprint: str
    invoice_date: str
    submission_date: str
    line_items_summary: Optional[str] = "General services & operational supplies"
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

class BankEvidence(BaseModel):
    submitted_fingerprint: str
    master_fingerprint: Optional[str] = None
    fingerprint_match: bool
    recent_change_detected: bool
    days_since_account_change: Optional[int] = None
    risk_level: Literal["NORMAL", "HIGH_RISK_RECENT_CHANGE", "FIRST_TIME_VENDOR_UNVERIFIED"]
    details: str

class DuplicateCandidate(BaseModel):
    matched_invoice_id: str
    match_type: Literal["EXACT_DUPLICATE", "NEAR_DUPLICATE_SAME_AMOUNT", "NEAR_DUPLICATE_WINDOW"]
    matched_amount: float
    matched_date: str
    date_difference_days: int
    similarity_score: float
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

class EvidenceDossier(BaseModel):
    invoice_id: str
    vendor_name: str
    amount: float
    invoice_date: str
    submission_date: str
    po_evidence: POEvidence
    bank_evidence: BankEvidence
    duplicate_evidence: DuplicateEvidence
    vendor_history_evidence: VendorHistoryEvidence
    structuring_evidence: StructuringEvidence
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
    dossier_summary: Optional[Dict[str, Any]] = None
    processed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

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
    
    auto_resolved_pct: float # auto_approved + reject_duplicate + escalate_fraud (safely handled with evidence without human blind-spot)
    human_routing_pct: float # held for review
    
    duplicate_metrics: ClassMetrics
    fraud_metrics: ClassMetrics
    legitimate_false_positive_count: int # Legitimate invoices incorrectly escalated or rejected
    legitimate_false_positive_rate: float
    
    avg_evidence_citations_per_non_approval: float
    structuring_flagship: StructuringFlagshipMetric
