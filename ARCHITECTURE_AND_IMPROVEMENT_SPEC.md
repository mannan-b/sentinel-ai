# 🛡️ Sentinel AP Agent: Deep Architecture, System Specification & AI Reviewer Dossier

> **Document Purpose**: This document provides a rigorous, component-by-component architectural specification of the **Sentinel AP Fraud & Duplicate-Payment Control Agent**. It is explicitly formatted to enable an external AI model or senior software architect to evaluate the codebase, identify architectural bottlenecks, discover edge cases, and propose high-impact improvements across backend engineering, machine learning/LLM integration, financial forensic algorithms, and frontend interactivity.

---

## 1. Executive Summary & Problem Domain

### 1.1 The Enterprise Problem
Enterprise Accounts Payable (AP) departments process thousands of supplier invoices monthly. Traditional Rule-Based Workflow Automation (RPA) and standard optical character recognition (OCR) systems suffer from two fatal failure modes:
1. **Isolated Single-Invoice Classification (Local Context Blindness)**: Scanners evaluate each invoice row in a vacuum. They fail to detect multi-invoice patterns such as **structuring (smurfing)**—where a dishonest supplier splits a $40,000 project into four $9,500 bills over 72 hours to bypass dual-signoff thresholds.
2. **Black-Box Probabilistic Guessing**: Traditional ML models produce bare confidence scores (e.g., `Risk: 0.82`) without checkable evidence, causing high false-positive alert fatigue or premature rejection of legitimate vendor relationships.

### 1.2 The Sentinel Thesis
Sentinel replaces isolated scoring with a **two-tier forensic pipeline**:
- **Tier 1 (Deterministic Zero-Hallucination Evidence Layer)**: Gathers mathematical, temporal, relational, and batch-level cross-record facts into a typed `EvidenceDossier`.
- **Tier 2 (Evidence-Grounded Verdict Layer)**: Synthesizes the dossier into one of four auditable actions (`auto_approve`, `hold_for_review`, `escalate_fraud`, `reject_duplicate`), mandating explicit **evidence citations** for every non-approval action.

---

## 2. Full System Architecture & Data Flow

```
                                  [Inbound AP Invoice Batch]
                                             │
                                             ▼
                             ┌───────────────────────────────┐
                             │    Synthetic Data Generator   │
                             │     (backend/generator.py)    │
                             └───────────────┬───────────────┘
                                             │
                                             ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ TIER 1: DETERMINISTIC EVIDENCE ENGINE (backend/evidence.py)                            │
│                                                                                        │
│  ┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐ ┌──────────────┐ │
│  │ 1. PO Match &      │ │ 2. Bank Routing &  │ │ 3. Duplicate Scan  │ │ 4. Vendor    │ │
│  │    Tolerance (±5%) │ │    Fingerprint BEC │ │    (Exact / Near)  │ │    Profile   │ │
│  └─────────┬──────────┘ └─────────┬──────────┘ └─────────┬──────────┘ └──────┬───────┘ │
│            │                      │                      │                   │         │
│            └──────────────────────┼──────────────────────┴───────────────────┘         │
│                                   │                                                    │
│                                   ▼                                                    │
│               ┌──────────────────────────────────────────────┐                         │
│               │ 5. Cross-Batch Structuring (Smurfing) Matrix │                         │
│               └───────────────────┬──────────────────────────┘                         │
│                                   │                                                    │
│                                   ▼                                                    │
│                      [Structured EvidenceDossier]                                      │
└───────────────────────────────────┬────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ TIER 2: VERDICT & CITATION ENGINE (backend/agent.py)                                   │
│                                                                                        │
│   • Structured Reasoning & Citation Formatter                                          │
│   • Multi-Class Verdict Evaluator (Approve / Hold / Escalate / Reject)                 │
│   • Explicit Refusal Protocol (Refuses to guess on thin/conflicting evidence)          │
└───────────────────────────────────┬────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ TIER 3: EVALUATION & OPERATIONAL METRICS (backend/metrics.py)                          │
│                                                                                        │
│   • Ground Truth Confusion Matrices (Fraud & Duplicate Classes)                        │
│   • Automation / Auto-Resolution vs Human Review Routing Rate                         │
│   • False Positive Cost Impact on Legitimate Suppliers                                 │
│   • Evidence Citation Density (Avg facts / non-approval action)                        │
└───────────────────────────────────┬────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PRESENTATION & CONTROL PLANE (FastAPI backend/server.py + frontend/)                   │
│                                                                                        │
│   • Real-Time Batch Runner & Ingestion Visualizer                                      │
│   • Results Dashboard with Filterable Table & Inline Fact Pills                        │
│   • Flagship Structuring Investigation Banner & Timeline Flow                          │
│   • Interactive 5-Pillar Evidence Modal with Human-in-the-Loop Override                │
│   • Metrics & Forensic Scoring Lab                                                     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Component Breakdown & Implementation Analysis

### 3.1 Data Models & Schemas (`backend/models.py`)

The system relies on strict Pydantic v2 schemas:

1. **`Invoice`**:
   - `invoice_id`: String unique identifier.
   - `vendor_name`, `vendor_id`: Foreign key reference to master vendor data.
   - `amount`: Float currency value.
   - `po_reference`: Optional string reference to purchase order.
   - `vendor_bank_fingerprint`: Hash/token representing the remittance bank account & routing number.
   - `invoice_date`, `submission_date`: ISO-8601 date strings (`YYYY-MM-DD`).
   - `ground_truth_label`: Hidden enum (`legitimate`, `duplicate`, `fraud_risk`, `needs_review`) used strictly in `metrics.py` for audit scorecard generation. Never exposed to the verdict agent.

2. **`EvidenceDossier`**:
   - `po_evidence`: Status (`EXACT_MATCH`, `WITHIN_TOLERANCE`, `AMOUNT_EXCEEDED`, `NO_PO_REFERENCED`, `INVALID_PO_REFERENCE`), delta percentage, approved amount vs billed amount.
   - `bank_evidence`: Master fingerprint vs submitted, `days_since_account_change`, risk level (`NORMAL`, `HIGH_RISK_RECENT_CHANGE`, `FIRST_TIME_VENDOR_UNVERIFIED`).
   - `duplicate_evidence`: `exact_duplicate_found`, `near_duplicate_found`, similarity score, list of `DuplicateCandidate` objects with candidate IDs and date differences.
   - `vendor_history_evidence`: Historical transaction count, historical average amount, ratio of current invoice to average, first-time large invoice flag.
   - `structuring_evidence`: `in_structuring_cluster` (Boolean), `cluster_invoice_ids` (List[str]), `cluster_total_amount`, individual amounts, threshold limit ($10,000.00), and window span in days.

3. **`AgentVerdict`**:
   - `verdict`: `auto_approve` | `hold_for_review` | `escalate_fraud` | `reject_duplicate`.
   - `confidence`: Float between 0.0 and 1.0.
   - `cited_evidence`: List of `CitedEvidenceItem` records containing `field_path`, `observed_value`, and `significance`.
   - `primary_reason`: Human-readable forensic finding.
   - `recommended_action`: Prescriptive AP remediation step.

---

### 3.2 Synthetic Data Generator (`backend/generator.py`)

A deterministic generator parameterized by `seed` and `total_invoices` (50–100 records). It deliberately creates a realistic distribution:

- **Clean Baseline (~75%+)**: Legitimate invoices from established vendors matching active POs within 0–2% variance and matching bank fingerprints.
- **Engineered Forensic Attacks & Anomalies**:
  1. **Cross-Batch Structuring (Smurfing)**: *Apex Security & Guarding LLC* splits a $38,000 obligation into 4 un-PO'd invoices of $9,500 each within a 3-day window to evade the $10,000 threshold.
  2. **Business Email Compromise (BEC) / Bank Account Takeover**: *CyberShield Defense Corp* invoice where the bank routing fingerprint was changed 2 days prior to submission.
  3. **First-Time Vendor Outlier**: Unknown vendor *Titanium Cybernetic Global Inc* submitting a $48,750 un-PO'd invoice with zero historical relationship.
  4. **Exact Duplicate Resubmission**: *CloudScale Infrastructure LLC* invoice resubmitted 4 days later with identical billing parameters.
  5. **Near Duplicate**: *Metro Logistics & Freight* invoice with identical amount ($6,700) and vendor submitted within a 2-day window with modified invoice ID.
  6. **Orphan / Missing PO Invoices**: Established vendors submitting bills with null or non-existent PO numbers.
  7. **PO Variance Violation**: Invoice exceeding approved PO by +35% (violating the 5% policy tolerance limit).

---

### 3.3 Deterministic Evidence Gathering Layer (`backend/evidence.py`)

The evidence layer executes non-probabilistic checks across 5 forensic dimensions:

1. **PO Tolerance Check**:
   $$\Delta\% = \frac{\text{Invoice Amount} - \text{PO Amount}}{\text{PO Amount}} \times 100$$
   - If $|\Delta\%| \le 0.001\% \rightarrow \text{EXACT\_MATCH}$
   - If $0 < \Delta\% \le 5.0\% \rightarrow \text{WITHIN\_TOLERANCE}$
   - If $\Delta\% > 5.0\% \rightarrow \text{AMOUNT\_EXCEEDED}$
   - If PO reference missing $\rightarrow \text{NO\_PO\_REFERENCED}$
   - If PO reference not in registry $\rightarrow \text{INVALID\_PO\_REFERENCE}$

2. **Bank Account Fingerprint Verification**:
   - Compares invoice fingerprint against vendor master record.
   - Checks if account was updated within the last 30 days (`days_since_account_change \le 30`).
   - Flags `HIGH_RISK_RECENT_CHANGE` if mismatched or recently altered.

3. **Batch-Level Duplicate Collision Scanning**:
   - Compares every invoice against all other records in the batch.
   - Chronological ordering logic: Distinguishes predecessor (original) from subsequent duplicate copies using `submission_date` and ID suffixes (`-DUP`, `-B`).
   - Computes similarity decay over temporal distance: $\text{Score} = 0.90 - (\text{days\_diff} \times 0.02)$.

4. **Cross-Batch Structuring (Smurfing) Scan**:
   - Groups invoices by vendor across the entire batch.
   - Filters for invoices within the sub-threshold risk band: $\$8,000.00 \le \text{Amount} < \$10,000.00$ without pre-approved POs.
   - If $\ge 3$ invoices exist within a $\le 5\text{-day}$ window:
     - Tags all participating invoices as an active structuring cluster.
     - Calculates combined obligation ($\sum \text{Amounts}$).
     - Creates structured cluster evidence attached to all constituent invoices.

---

### 3.4 Verdict & Citation Layer (`backend/agent.py`)

Renders auditable verdicts using an explicit rubric:

| Condition | Verdict | Required Citations |
| :--- | :--- | :--- |
| `structuring_evidence.in_structuring_cluster == True` | `escalate_fraud` | Cluster count, individual amounts, combined sum, evaded threshold |
| `bank_evidence.risk_level == 'HIGH_RISK_RECENT_CHANGE'` | `escalate_fraud` | Submitted fingerprint, master fingerprint, days since change |
| `duplicate_evidence.is_duplicate_risk == True` | `reject_duplicate` | Matched invoice ID, similarity score, match type |
| First-time vendor with amount > $10,000 & no PO | `hold_for_review` | First-time flag, invoice amount, PO status |
| PO amount exceeded > 5% tolerance | `hold_for_review` | PO approved amount, invoice amount, $\Delta\%$ variance |
| Missing or invalid PO on established vendor | `hold_for_review` | PO status, submitted reference |
| All checks clean (3-way match, verified bank, no duplicates) | `auto_approve` | Clean PO match status, verified bank status, 0 duplicate flags |

---

### 3.5 Scoring & Evaluation Metrics (`backend/metrics.py`)

Evaluates performance against hidden ground truth labels:
- **Binary Metrics per Class (Fraud & Duplicates)**:
  $$\text{Precision} = \frac{TP}{TP + FP}, \quad \text{Recall} = \frac{TP}{TP + FN}, \quad F_1 = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$
- **False Positive Rate on Legitimate Vendors**:
  $$\text{FPR}_{\text{legit}} = \frac{\text{Clean Invoices Flagged as Fraud/Reject}}{\text{Total Invoices}}$$
- **Auto-Resolution Rate vs Human Routing**:
  $$\text{Auto-Resolved } \% = \frac{\text{Approved} + \text{Duplicates Rejected} + \text{Fraud Escalated}}{\text{Total Invoices}} \times 100$$
- **Evidence Citation Density**: Average number of cited facts per non-approval decision.

---

## 4. Current Constraints & Architectural Simplifications

To prepare an external AI model to suggest meaningful improvements, here is a transparent inventory of current architectural simplifications:

1. **In-Memory Batch State**: `BatchState` in `backend/server.py` stores batch data in Python process memory. A server restart resets dynamic state (though deterministic seed generation maintains reproducibility).
2. **Synchronous Single-Process Execution**: Evidence extraction and verdict generation run synchronously in the FastAPI request-response cycle.
3. **Regex/Heuristic Similarity for Duplicates**: Duplicate detection uses exact vendor ID match + amount match + date window heuristics rather than semantic NLP/embeddings on line-item descriptions.
4. **Static Hardcoded Thresholds**: Approval threshold ($10,000.00) and PO tolerance (5%) are hardcoded constants rather than configurable tenant-level policy rules.
5. **Simulated Vendor Master Database**: Master vendor and PO records are generated alongside the batch rather than queried from an external SQL/ERP system (e.g., SAP, NetSuite, QuickBooks).

---

## 5. High-Impact Vectors for Improvement (Prompt Guide for Reviewer AI)

When asking another AI model to review or improve this project, prompt it to focus on the following high-value architectural vectors:

### Vector A: Advanced Multi-Agent Orchestration & Real LLM Integration
- How can we implement an asynchronous **LangGraph / CrewAI / DSPy** multi-agent pipeline where specialized sub-agents (e.g., *Contract Compliance Agent*, *Forensic Entity Resolver*, *Tax & Sanction Screener*) perform parallel reasoning?
- How should we implement prompt caching, fallback retry circuits, and structured output parsing (Pydantic Output Parser) with streaming responses via Server-Sent Events (SSE)?

### Vector B: Vector Embeddings & Fuzzy Semantic Duplicate Detection
- Instead of simple amount + date window matching, how can we integrate sentence transformers (e.g., `all-MiniLM-L6-v2`) and vector search (e.g., FAISS or pgvector) to detect semantic near-duplicates where invoice descriptions and line-items are paraphrased (e.g., "Monthly cloud compute hosting" vs "Aug 2026 AWS hosting infrastructure charges")?

### Vector C: Graph-Based Entity Resolution & Network Fraud Analysis
- How can we model vendors, bank account fingerprints, tax IDs, physical addresses, and invoice submitters as an in-memory knowledge graph (e.g., NetworkX or Neo4j) to detect **vendor collusion rings** (e.g., different vendor names sharing the same bank routing number or phone number)?

### Vector D: Production Database & Multi-Tenant AP Policy Engine
- How can we refactor `models.py` into SQLAlchemy / PostgreSQL models with Alembic migrations, database pooling, and dynamic tenant policy configuration (e.g., customizable per-department approval limits, tolerance bands, and dual-authorization workflows)?

### Vector E: Multimodal Document Ingestion (OCR & LayoutLM)
- How can we add a file upload endpoint for PDF/image invoices that extracts structured key-value pairs using multimodal models (Gemini Flash Vision / LayoutLMv3) before passing them into the Sentinel Evidence Engine?

---

## 6. How to Run & Verify

```bash
# 1. Install dependencies
pip install fastapi uvicorn pydantic tabulate pytest

# 2. Run automated verification test suite
python tests/test_pipeline.py

# 3. Inspect dataset & evaluate metrics via CLI
python seed_data.py --seed 42 --size 75

# 4. Launch web application
python run.py
# Access dashboard at http://127.0.0.1:8000/
```
