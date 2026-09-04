import os
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.models import (
    Invoice, PurchaseOrder, VendorMaster, EvidenceDossier,
    AgentVerdict, BatchScorecard
)
from backend.generator import generate_synthetic_batch
from backend.evidence import EvidenceEngine
from backend.agent import SentinelAPAgent
from backend.metrics import compute_batch_scorecard

app = FastAPI(
    title="Sentinel AP Fraud & Duplicate-Payment Control Agent",
    description="Intelligent AP Fraud, Duplicate-Payment, and Cross-Batch Structuring Control Engine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory batch state storage
class BatchState:
    def __init__(self):
        self.seed: int = 42
        self.size: int = 75
        self.invoices: list[Invoice] = []
        self.purchase_orders: list[PurchaseOrder] = []
        self.vendor_masters: list[VendorMaster] = []
        self.recent_bank_changes: dict[str, int] = {}
        self.dossiers: dict[str, EvidenceDossier] = {}
        self.verdicts: list[AgentVerdict] = []
        self.scorecard: Optional[BatchScorecard] = None
        self.is_analyzed: bool = False

state = BatchState()
agent = SentinelAPAgent()

def initialize_batch(seed: int = 42, size: int = 75):
    state.seed = seed
    state.size = size
    invs, pos, vms, bank_changes = generate_synthetic_batch(seed=seed, total_invoices=size)
    state.invoices = invs
    state.purchase_orders = pos
    state.vendor_masters = vms
    state.recent_bank_changes = bank_changes
    state.dossiers = {}
    state.verdicts = []
    state.scorecard = None
    state.is_analyzed = False

# Auto-initialize batch with default seed
initialize_batch(42, 75)

class GenerateRequest(BaseModel):
    seed: int = 42
    size: int = 75

class OverrideRequest(BaseModel):
    new_verdict: str
    reviewer_notes: str

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Sentinel AP Control Agent",
        "batch_loaded": len(state.invoices) > 0,
        "is_analyzed": state.is_analyzed,
        "invoice_count": len(state.invoices)
    }

@app.post("/api/batch/generate")
def generate_batch(req: GenerateRequest):
    initialize_batch(seed=req.seed, size=req.size)
    return {
        "message": f"Successfully generated synthetic AP batch with seed={req.seed} and {len(state.invoices)} invoices.",
        "invoice_count": len(state.invoices),
        "po_count": len(state.purchase_orders),
        "vendor_count": len(state.vendor_masters),
        "seed": state.seed
    }

@app.post("/api/batch/analyze")
def analyze_batch():
    if not state.invoices:
        initialize_batch()

    # 1. Deterministic Evidence Gathering Layer
    engine = EvidenceEngine(
        purchase_orders=state.purchase_orders,
        vendor_masters=state.vendor_masters,
        recent_bank_changes=state.recent_bank_changes
    )
    
    dossiers_map: dict[str, EvidenceDossier] = {}
    for inv in state.invoices:
        dossiers_map[inv.invoice_id] = engine.build_dossier(inv, state.invoices)
    
    state.dossiers = dossiers_map

    # 2. Agent Verdict Layer
    state.verdicts = agent.evaluate_batch(state.invoices, state.dossiers)

    # 3. Scoring & Metrics Layer
    state.scorecard = compute_batch_scorecard(state.invoices, state.verdicts, state.dossiers)
    state.is_analyzed = True

    return {
        "status": "success",
        "total_analyzed": len(state.verdicts),
        "scorecard": state.scorecard,
        "structuring_flagship": state.scorecard.structuring_flagship
    }

@app.get("/api/batch/latest")
def get_latest_batch():
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
        "vendors": [v.dict() for v in state.vendor_masters],
        "purchase_orders": [p.dict() for p in state.purchase_orders]
    }

@app.get("/api/invoices/{invoice_id}/dossier")
def get_invoice_dossier(invoice_id: str):
    inv = next((i for i in state.invoices if i.invoice_id == invoice_id), None)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    dossier = state.dossiers.get(invoice_id)
    verdict = next((v for v in state.verdicts if v.invoice_id == invoice_id), None)
    
    # Associated PO if exists
    po = next((p for p in state.purchase_orders if p.po_number == inv.po_reference), None)
    # Vendor info
    vendor = next((vm for vm in state.vendor_masters if vm.vendor_id == inv.vendor_id), None)

    return {
        "invoice": inv,
        "verdict": verdict,
        "dossier": dossier,
        "purchase_order": po,
        "vendor": vendor,
        "ground_truth": {
            "label": inv.ground_truth_label,
            "reason": inv.ground_truth_reason
        }
    }

@app.post("/api/invoice/{invoice_id}/override")
def override_invoice_verdict(invoice_id: str, req: OverrideRequest):
    verdict = next((v for v in state.verdicts if v.invoice_id == invoice_id), None)
    if not verdict:
        raise HTTPException(status_code=404, detail="Invoice verdict not found")
    
    verdict.verdict = req.new_verdict # type: ignore
    verdict.primary_reason = f"[HUMAN OVERRIDE]: {req.reviewer_notes}"
    verdict.confidence = 1.0

    # Recalculate scorecard
    state.scorecard = compute_batch_scorecard(state.invoices, state.verdicts, state.dossiers)
    
    return {
        "message": f"Successfully updated verdict for {invoice_id} to {req.new_verdict}",
        "verdict": verdict,
        "updated_scorecard": state.scorecard
    }

# Mount static frontend
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Sentinel AP Backend is running. Frontend static directory is initializing."}
