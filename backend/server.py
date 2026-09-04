import os
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.models import (
    Invoice, PurchaseOrder, GoodsReceipt, VendorMaster, EvidenceDossier,
    AgentVerdict, BatchScorecard, FinanceException, ExceptionGroup,
    BankChangeAlert, CashPositionSummary, FinanceControlPolicy, AuditEvent
)
from backend.generator import generate_synthetic_batch
from backend.evidence import EvidenceEngine
from backend.agent import SentinelAPAgent
from backend.controller import FinanceOperationsController
from backend.metrics import compute_batch_scorecard
from backend.audit import audit_trail

app = FastAPI(
    title="Sentinel — AI Finance Controller",
    description="Autonomous AP 3-Way Reconciliation, Exception Resolution, Cash Position & Fraud Control Engine",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BatchState:
    def __init__(self):
        self.seed: int = 42
        self.size: int = 75
        self.policy: FinanceControlPolicy = FinanceControlPolicy()
        self.invoices: List[Invoice] = []
        self.purchase_orders: List[PurchaseOrder] = []
        self.goods_receipts: List[GoodsReceipt] = []
        self.vendor_masters: List[VendorMaster] = []
        self.recent_bank_changes: Dict[str, int] = {}
        
        self.dossiers: Dict[str, EvidenceDossier] = {}
        self.verdicts: List[AgentVerdict] = []
        self.exceptions: List[FinanceException] = []
        self.exception_groups: List[ExceptionGroup] = []
        self.bank_alerts: List[BankChangeAlert] = []
        self.cash_position: Optional[CashPositionSummary] = None
        self.scorecard: Optional[BatchScorecard] = None
        self.is_analyzed: bool = False

state = BatchState()

def initialize_batch(seed: int = 42, size: int = 75):
    state.seed = seed
    state.size = size
    invs, pos, grns, vms, bank_changes = generate_synthetic_batch(seed=seed, total_invoices=size)
    state.invoices = invs
    state.purchase_orders = pos
    state.goods_receipts = grns
    state.vendor_masters = vms
    state.recent_bank_changes = bank_changes
    state.dossiers = {}
    state.verdicts = []
    state.exceptions = []
    state.exception_groups = []
    state.bank_alerts = []
    state.cash_position = None
    state.scorecard = None
    state.is_analyzed = False
    
    audit_trail.log(
        action="BATCH_INGESTED",
        actor="SYSTEM_SCHEDULER",
        affected_record=f"Batch_Seed_{seed}",
        new_state=f"{len(invs)} invoices ingested",
        reason=f"Synthetic ERP batch generation (seed={seed}, size={size})"
    )

# Auto-initialize
initialize_batch(42, 75)

def run_controller_pipeline():
    # 1. Deterministic Evidence Engine (3-Way Matching, Hybrid Duplicate, Bank, Structuring, Collusion)
    evidence_engine = EvidenceEngine(
        purchase_orders=state.purchase_orders,
        goods_receipts=state.goods_receipts,
        vendor_masters=state.vendor_masters,
        recent_bank_changes=state.recent_bank_changes,
        policy=state.policy
    )
    
    dossiers_map: Dict[str, EvidenceDossier] = {}
    for inv in state.invoices:
        dossiers_map[inv.invoice_id] = evidence_engine.build_dossier(inv, state.invoices)
    state.dossiers = dossiers_map

    # 2. AI Verdict & Controller Layer
    agent = SentinelAPAgent(policy=state.policy)
    state.verdicts = agent.evaluate_batch(state.invoices, state.dossiers)

    # 3. Exception Resolution Engine & Grouping
    controller = FinanceOperationsController(policy=state.policy)
    state.exceptions = controller.generate_exceptions(state.invoices, state.dossiers)
    state.exception_groups = controller.group_exceptions(state.exceptions)
    state.bank_alerts = controller.generate_bank_change_alerts(
        state.invoices, state.vendor_masters, state.recent_bank_changes
    )

    # 4. Payment Queue & Cash Outflow Forecasting
    state.cash_position = controller.update_payment_queue_and_cash_position(
        state.invoices, state.dossiers, state.bank_alerts
    )

    # 5. Scorecard & Metrics
    state.scorecard = compute_batch_scorecard(
        state.invoices, state.verdicts, state.dossiers, state.exceptions
    )
    state.is_analyzed = True

    audit_trail.log(
        action="CONTROL_PIPELINE_EXECUTED",
        actor="AI_FINANCE_CONTROLLER",
        affected_record=f"Batch_{state.seed}",
        new_state=f"{len(state.verdicts)} reconciled, {len(state.exceptions)} exceptions",
        reason="Full 3-way reconciliation, duplicate scan, and cash position calculation executed."
    )

class GenerateRequest(BaseModel):
    seed: int = 42
    size: int = 75

class OverrideRequest(BaseModel):
    new_verdict: str
    reviewer_notes: str

class ResolveExceptionRequest(BaseModel):
    action: str # "RESOLVED" | "ESCALATED" | "SHORT_PAY"
    resolution_notes: str
    assigned_owner: Optional[str] = None

class BankControlVerifyRequest(BaseModel):
    control_name: str # "independent_phone_verified" | "cfo_signoff" | "account_ownership_verified" | "cooling_period_elapsed"
    status: str # "VERIFIED" | "FAILED" | "PENDING"
    notes: Optional[str] = "Supervisor control verification"

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Sentinel AI Finance Controller",
        "version": "2.0.0",
        "batch_loaded": len(state.invoices) > 0,
        "is_analyzed": state.is_analyzed,
        "invoice_count": len(state.invoices),
        "exceptions_count": len(state.exceptions)
    }

@app.post("/api/batch/generate")
def generate_batch(req: GenerateRequest):
    initialize_batch(seed=req.seed, size=req.size)
    return {
        "message": f"Successfully generated synthetic AP batch with seed={req.seed} and {len(state.invoices)} invoices.",
        "invoice_count": len(state.invoices),
        "po_count": len(state.purchase_orders),
        "grn_count": len(state.goods_receipts),
        "vendor_count": len(state.vendor_masters),
        "seed": state.seed
    }

@app.post("/api/batch/analyze")
def analyze_batch():
    if not state.invoices:
        initialize_batch()
    run_controller_pipeline()
    return {
        "status": "success",
        "total_analyzed": len(state.verdicts),
        "scorecard": state.scorecard,
        "cash_position": state.cash_position,
        "exceptions_count": len(state.exceptions),
        "exception_groups_count": len(state.exception_groups),
        "bank_alerts_count": len(state.bank_alerts)
    }

@app.get("/api/batch/latest")
def get_latest_batch():
    if not state.is_analyzed:
        run_controller_pipeline()

    verdict_dict = {v.invoice_id: v for v in state.verdicts}
    
    combined_items = []
    for inv in state.invoices:
        v = verdict_dict.get(inv.invoice_id)
        dossier = state.dossiers.get(inv.invoice_id)
        combined_items.append({
            "invoice": inv,
            "verdict": v,
            "dossier": dossier,
            "ground_truth": {
                "label": inv.ground_truth_label,
                "reason": inv.ground_truth_reason
            }
        })

    return {
        "seed": state.seed,
        "is_analyzed": state.is_analyzed,
        "total_count": len(state.invoices),
        "invoices": combined_items,
        "scorecard": state.scorecard,
        "cash_position": state.cash_position,
        "exceptions": state.exceptions,
        "exception_groups": state.exception_groups,
        "bank_alerts": state.bank_alerts,
        "policy": state.policy,
        "vendors": [v.dict() for v in state.vendor_masters],
        "purchase_orders": [p.dict() for p in state.purchase_orders],
        "goods_receipts": [g.dict() for g in state.goods_receipts]
    }

@app.get("/api/invoices/{invoice_id}/dossier")
def get_invoice_dossier(invoice_id: str):
    inv = next((i for i in state.invoices if i.invoice_id == invoice_id), None)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    dossier = state.dossiers.get(invoice_id)
    verdict = next((v for v in state.verdicts if v.invoice_id == invoice_id), None)
    po = next((p for p in state.purchase_orders if p.po_number == inv.po_reference), None)
    grn = next((g for g in state.goods_receipts if g.po_reference == inv.po_reference), None)
    vendor = next((vm for vm in state.vendor_masters if vm.vendor_id == inv.vendor_id), None)
    exception = next((e for e in state.exceptions if e.invoice_id == invoice_id), None)

    return {
        "invoice": inv,
        "verdict": verdict,
        "dossier": dossier,
        "purchase_order": po,
        "goods_receipt": grn,
        "vendor": vendor,
        "exception": exception,
        "ground_truth": {
            "label": inv.ground_truth_label,
            "reason": inv.ground_truth_reason
        }
    }

@app.post("/api/invoice/{invoice_id}/override")
def override_invoice_verdict(invoice_id: str, req: OverrideRequest):
    verdict = next((v for v in state.verdicts if v.invoice_id == invoice_id), None)
    inv = next((i for i in state.invoices if i.invoice_id == invoice_id), None)
    if not verdict or not inv:
        raise HTTPException(status_code=404, detail="Invoice verdict not found")
    
    prev_verdict = verdict.verdict
    verdict.verdict = req.new_verdict # type: ignore
    verdict.primary_reason = f"[HUMAN OVERRIDE]: {req.reviewer_notes}"
    verdict.confidence = 1.0

    # Update payment status
    if req.new_verdict == "auto_approve":
        inv.payment_status = "READY_FOR_PAYMENT"
        inv.approval_status = "APPROVED"
    elif req.new_verdict == "reject_duplicate":
        inv.payment_status = "DUPLICATE_REJECTED"
        inv.approval_status = "REJECTED"
    elif req.new_verdict == "escalate_fraud":
        inv.payment_status = "FRAUD_HOLD"
        inv.approval_status = "ESCALATED"

    # Recalculate scorecard & cash position
    controller = FinanceOperationsController(policy=state.policy)
    state.cash_position = controller.update_payment_queue_and_cash_position(
        state.invoices, state.dossiers, state.bank_alerts
    )
    state.scorecard = compute_batch_scorecard(state.invoices, state.verdicts, state.dossiers, state.exceptions)
    
    audit_trail.log(
        action="VERDICT_OVERRIDE",
        actor="AP_SUPERVISOR",
        affected_record=invoice_id,
        previous_state=prev_verdict,
        new_state=req.new_verdict,
        reason=req.reviewer_notes
    )

    return {
        "message": f"Successfully updated verdict for {invoice_id} to {req.new_verdict}",
        "verdict": verdict,
        "updated_scorecard": state.scorecard,
        "cash_position": state.cash_position
    }

@app.post("/api/exceptions/{exception_id}/resolve")
def resolve_exception(exception_id: str, req: ResolveExceptionRequest):
    ex = next((e for e in state.exceptions if e.exception_id == exception_id), None)
    if not ex:
        raise HTTPException(status_code=404, detail="Exception record not found")
    
    prev_status = ex.status
    ex.status = "RESOLVED" if req.action in ["RESOLVED", "SHORT_PAY"] else "ESCALATED"
    ex.resolution_notes = req.resolution_notes
    ex.resolved_by = "AP_CONTROLLER"
    ex.resolved_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    # Update corresponding invoice status
    inv = next((i for i in state.invoices if i.invoice_id == ex.invoice_id), None)
    if inv:
        if req.action == "RESOLVED":
            inv.payment_status = "READY_FOR_PAYMENT"
            inv.approval_status = "APPROVED"
        elif req.action == "SHORT_PAY":
            inv.payment_status = "READY_FOR_PAYMENT"
            inv.approval_status = "APPROVED"
        elif req.action == "ESCALATED":
            inv.payment_status = "FRAUD_HOLD"
            inv.approval_status = "ESCALATED"

    # Refresh scorecard & cash position
    controller = FinanceOperationsController(policy=state.policy)
    state.cash_position = controller.update_payment_queue_and_cash_position(
        state.invoices, state.dossiers, state.bank_alerts
    )
    state.scorecard = compute_batch_scorecard(state.invoices, state.verdicts, state.dossiers, state.exceptions)

    audit_trail.log(
        action="EXCEPTION_RESOLVED" if ex.status == "RESOLVED" else "EXCEPTION_ESCALATED",
        actor="AP_CONTROLLER",
        affected_record=exception_id,
        previous_state=prev_status,
        new_state=ex.status,
        reason=req.resolution_notes
    )

    return {
        "message": f"Exception {exception_id} updated to {ex.status}",
        "exception": ex,
        "scorecard": state.scorecard,
        "cash_position": state.cash_position
    }

@app.post("/api/bank-controls/{vendor_id}/verify")
def verify_bank_control(vendor_id: str, req: BankControlVerifyRequest):
    alert = next((a for a in state.bank_alerts if a.vendor_id == vendor_id), None)
    if not alert:
        raise HTTPException(status_code=404, detail="Bank change alert not found for vendor")

    if req.control_name == "independent_phone_verified":
        alert.independent_phone_verified = req.status # type: ignore
    elif req.control_name == "cfo_signoff":
        alert.cfo_signoff = req.status # type: ignore
    elif req.control_name == "account_ownership_verified":
        alert.account_ownership_verified = req.status # type: ignore
    elif req.control_name == "cooling_period_elapsed":
        alert.cooling_period_elapsed = req.status # type: ignore

    # Check if all 4 are satisfied
    all_pass = (
        alert.independent_phone_verified == "VERIFIED" and
        alert.cfo_signoff == "VERIFIED" and
        alert.account_ownership_verified == "VERIFIED" and
        alert.cooling_period_elapsed == "VERIFIED"
    )
    alert.all_controls_satisfied = all_pass

    # If all verified, release hold on invoices
    if all_pass:
        for inv_id in alert.affected_invoice_ids:
            inv = next((i for i in state.invoices if i.invoice_id == inv_id), None)
            if inv:
                inv.payment_status = "READY_FOR_PAYMENT"
                inv.approval_status = "APPROVED"

    controller = FinanceOperationsController(policy=state.policy)
    state.cash_position = controller.update_payment_queue_and_cash_position(
        state.invoices, state.dossiers, state.bank_alerts
    )
    state.scorecard = compute_batch_scorecard(state.invoices, state.verdicts, state.dossiers, state.exceptions)

    audit_trail.log(
        action="BANK_CONTROL_UPDATED",
        actor="COMPLIANCE_OFFICER",
        affected_record=f"Vendor_{vendor_id}",
        new_state=f"{req.control_name}: {req.status}",
        reason=req.notes or "BEC checklist verification"
    )

    return {
        "message": f"Bank control '{req.control_name}' set to {req.status}",
        "alert": alert,
        "cash_position": state.cash_position
    }

@app.post("/api/policy/update")
def update_policy(policy: FinanceControlPolicy):
    old_tolerance = state.policy.po_tolerance_pct
    state.policy = policy
    
    audit_trail.log(
        action="POLICY_UPDATED",
        actor="FINANCE_ADMIN",
        affected_record="ControlPolicy",
        previous_state=f"PO Tolerance: {old_tolerance}%",
        new_state=f"PO Tolerance: {policy.po_tolerance_pct}%, Approval: ${policy.approval_threshold:,.0f}",
        reason="Admin updated financial control threshold policies."
    )

    # Re-evaluate batch with updated policy
    run_controller_pipeline()

    return {
        "message": "Finance control policy updated and batch re-evaluated.",
        "policy": state.policy,
        "scorecard": state.scorecard,
        "cash_position": state.cash_position
    }

@app.get("/api/audit-trail")
def get_audit_trail():
    return {
        "total_events": len(audit_trail.events),
        "events": audit_trail.get_events(limit=100)
    }

@app.get("/api/cash-position")
def get_cash_position():
    if not state.cash_position:
        run_controller_pipeline()
    return state.cash_position

# Mount static frontend
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Sentinel AI Finance Controller is running."}
