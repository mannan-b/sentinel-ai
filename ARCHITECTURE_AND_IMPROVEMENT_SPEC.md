# 🛡️ Sentinel AI Finance Controller: Deep Architecture, System Specification & Improvement Blueprint

> **Document Purpose**: This document provides a rigorous, component-by-component architectural specification of the **Sentinel AI Finance Controller**. It details how the system closes the complete finance-operations loop:
> 
> $$\text{INGEST} \longrightarrow \text{RECONCILE (3-Way)} \longrightarrow \text{EXPLAIN} \longrightarrow \text{RESOLVE / ESCALATE} \longrightarrow \text{PAYMENT QUEUE} \longrightarrow \text{CASH POSITION} \longrightarrow \text{MEASURE}$$
> 
> It is explicitly formatted to enable external AI models, software architects, and enterprise finance engineers to evaluate the system, verify forensic algorithms, understand state transitions, and build enterprise extensions.

---

## 1. Executive Summary & Problem Domain

### 1.1 The Enterprise Problem
Enterprise Accounts Payable (AP) departments process thousands of supplier invoices monthly. Traditional Rule-Based Workflow Automation (RPA) and standard optical character recognition (OCR) systems suffer from three fatal failure modes:
1. **Isolated Single-Invoice Classification (Local Context Blindness)**: Scanners evaluate each invoice row in a vacuum. They fail to detect multi-invoice patterns such as **structuring (smurfing)**—where a supplier splits a $40,000 obligation into multiple sub-$10,000 bills to bypass dual-signoff thresholds.
2. **Missing Operational Closed-Loop**: Most tools stop at "Exception detected." They fail to route issues to appropriate operational owners, estimate cash exposure, forecast forward payables outflow, or maintain an immutable audit trail.
3. **Black-Box Probabilistic Hallucination**: Pure LLM solutions perform arithmetic unreliably, invent financial discrepancies, or fail to substantiate claims with checkable forensic evidence.

### 1.2 The Sentinel Thesis
Sentinel replaces isolated scoring with a **deterministic evidence-grounded AI Finance Controller**:
- **Layer 1 (Deterministic Zero-Hallucination Evidence Layer)**: Performs rigorous mathematical comparisons for 3-Way Reconciliation ($\text{Invoice} \leftrightarrow \text{Purchase Order} \leftrightarrow \text{Goods Receipt Note}$), Two-Stage Hybrid Duplicate Scanning, BEC Bank Change detection, and Structuring Matrices without LLM arithmetic.
- **Layer 2 (Evidence-Grounded AI Controller & Citation Layer)**: Synthesizes deterministic evidence into structured controller decisions (`auto_approve`, `hold_for_review`, `escalate_fraud`, `reject_duplicate`), citing precise forensic facts and recommending next operational actions while enforcing strict refusal-to-guess protocols.
- **Layer 3 (Exception Resolution & Operational Lifecycle)**: Generates prioritized exceptions ($0-100$ priority score), assigns operational owners (`AP_CLERK`, `PROCUREMENT_BUYER`, `CONTROLLER`, `INTERNAL_AUDIT`), aggregates related issues, and surfaces historical resolution memory.
- **Layer 4 (Payment Queue & AP Cash Outflow Forecast)**: Calculates forward-looking cash outflow ($7\text{d}, 14\text{d}, 30\text{d}$) broken down into Approved Outflow, Held Outflow, High-Risk Outflow, and Cash at Risk.
- **Layer 5 (BEC Dual-Control Gate & Governance)**: Enforces an interactive 4-point verification checklist before releasing payments on altered bank accounts.
- **Layer 6 (Audit Trail & Evaluation Scorecard)**: Maintains an immutable event ledger and calculates operational metrics (Match Rate, Exception Rate, Auto-Resolution Rate, F1, FPR, and Value Prevented).

---

## 2. Full System Architecture & Data Flow

```
                                  [Inbound AP Invoice Batch]
                                              │
                                              ▼
                              ┌───────────────────────────────┐
                              │    Synthetic Data Generator   │
                              │     (backend/generator.py)    │
                              │  Invoices + POs + Dock GRNs   │
                              └───────────────┬───────────────┘
                                              │
                                              ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: DETERMINISTIC FORENSIC & RECONCILIATION ENGINE (backend/evidence.py)         │
│                                                                                        │
│  ┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────────────┐ │
│  │ 1. 3-Way Match        │ │ 2. Bank Routing &     │ │ 3. Two-Stage Hybrid Duplicate │ │
│  │    Invoice ↔ PO ↔ GRN │ │    BEC Fingerprint    │ │    Candidate Gen + Similarity │ │
│  │    (Qty, Price, Dock) │ │    Cooling Period     │ │    (Inv, Vendor, Amt, Date)   │ │
│  └───────────┬───────────┘ └───────────┬───────────┘ └───────────────┬───────────────┘ │
│              │                         │                             │                 │
│              └─────────────────────────┼─────────────────────────────┘                 │
│                                        │                                               │
│                                        ▼                                               │
│                    ┌────────────────────────────────────────┐                          │
│                    │ 4. Cross-Batch Structuring Matrix      │                          │
│                    │ 5. Shared Bank Account Collusion Scan  │                          │
│                    └───────────────────┬────────────────────┘                          │
│                                        │                                               │
│                                        ▼                                               │
│                           [Typed EvidenceDossier]                                      │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         │
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: EVIDENCE-GROUNDED AI CONTROLLER & CITATION ENGINE (backend/agent.py)          │
│                                                                                        │
│   • Structured Reasoning & Citation Formatter                                          │
│   • Controller Action Synthesizer (verdict, primary_reason, cited_evidence, next_step) │
│   • Explicit Refusal Protocol (Refuses to guess on thin / conflicting evidence)        │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         │
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: FINANCE OPERATIONS CONTROLLER & RESOLUTION ENGINE (backend/controller.py)     │
│                                                                                        │
│   • Exception Lifecycle (OPEN → AI_RECOMMENDED → HUMAN_REVIEW → RESOLVED / ESCALATED) │
│   • Deterministic Prioritization Scoring (0 - 100) & Operational Owner Assignment      │
│   • Operational Issue Aggregation (Groups multi-invoice vendor anomalies)             │
│   • Synthetic Historical Resolution Pattern Memory                                     │
│   • BEC Dual-Control Payment Release Gate (4-Point Verification Checklist)             │
│   • Forward AP Cash Outflow Forecast (0-7d, 8-14d, 15-30d, 30+d / Cash at Risk)       │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         │
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: IMMUTABLE AUDIT TRAIL & EVALUATION METRICS (backend/audit.py, metrics.py)     │
│                                                                                        │
│   • Centralized Immutable Event Ledger (Batch Ingestion, Decisions, Overrides, BEC)   │
│   • Operational KPIs: Match Rate, Exception Rate, Auto-Resolution vs Human Review Rate │
│   • Financial Risk Totals: Cash at Risk, Duplicate Prevented, Fraud Escalated          │
│   • Forensic Quality: Precision, Recall, F1, False Positive Rate, Citation Density     │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         │
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PRESENTATION & CONTROL CENTER (FastAPI backend/server.py + frontend/)                  │
│                                                                                        │
│   • Finance Control Center KPI Bar & Cash Outflow Forecast Cards                       │
│   • Filterable Invoices & 3-Way Reconciliation Status Grid with Inline Fact Badges     │
│   • Exception Resolution Workbench (Grouped Tickets, One-Click Modal Resolution)       │
│   • Payment Queue & AP Cash Maturity Schedule                                          │
│   • BEC Dual-Control Verification Modal & Release Workflow                             │
│   • Configurable Control Policy Drawer (PO Tolerance, Duplicate Thresh, Cooling Days)  │
│   • Immutable Audit Trail Timeline Stream                                              │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Component Breakdown & Implementation Analysis

### 3.1 Data Models & Schemas (`backend/models.py`)

The system uses strict Pydantic v2 schemas across all operational layers:

1. **`LineItem`**:
   - `line_id`: Unique identifier (`LINE-001`).
   - `description`: Goods/services description.
   - `quantity`: Float billed or received.
   - `unit_price`: Unit monetary rate.
   - `total_price`: Calculated total ($Q \times P$).

2. **`PurchaseOrder`**:
   - `po_id`: Unique PO identifier (`PO-7001`).
   - `vendor_id`, `vendor_name`: Supplier references.
   - `total_amount`: Approved spending ceiling.
   - `currency`: Default `USD`.
   - `line_items`: Approved line item details.
   - `created_date`, `status`: Status (`APPROVED`, `CLOSED`, etc.).

3. **`GoodsReceipt` (GRN)**:
   - `grn_id`: Receiving dock note ID (`GRN-9001`).
   - `po_reference`: Target purchase order.
   - `vendor_id`: Supplier reference.
   - `received_date`: Dock intake date.
   - `received_by`: Receiving dock agent name.
   - `line_items`: Actual physical count and condition received.
   - `status`: Dock status (`COMPLETE`, `PARTIAL`, `DAMAGED`).

4. **`Invoice`**:
   - `invoice_id`, `vendor_name`, `vendor_id`, `amount`, `po_reference`, `vendor_bank_fingerprint`, `invoice_date`, `submission_date`.
   - `line_items`: Invoiced line details.
   - `due_date`, `payment_terms` (`NET_15`, `NET_30`, `NET_60`, `IMMEDIATE`).
   - `payment_status`: `READY_FOR_PAYMENT`, `AWAITING_REVIEW`, `PAYMENT_HOLD`, `DUPLICATE_REJECTED`, `BLOCKED_BY_RECONCILIATION`, `RELEASED`.
   - `approval_status`: `PENDING`, `AUTO_APPROVED`, `HELD`, `ESCALATED`, `REJECTED`, `RESOLVED`.
   - `ground_truth_label`: Hidden evaluation label (`legitimate`, `duplicate`, `fraud_risk`, `needs_review`).

5. **`ReceiptEvidence` (3-Way Match)**:
   - `receipt_status`: `EXACT_3WAY_MATCH`, `WITHIN_TOLERANCE`, `QUANTITY_OVERBILLED`, `PRICE_MISMATCH`, `MISSING_GRN`, `PARTIAL_RECEIPT`, `EXTRA_LINE_ITEM`, `NO_PO_OR_RECEIPT`.
   - `invoiced_quantity`, `received_quantity`, `po_quantity`.
   - `invoiced_unit_price`, `po_unit_price`.
   - `quantity_delta`, `price_delta`, `discrepancy_amount`.

6. **`FinanceException` & `ExceptionGroup`**:
   - `exception_id`, `invoice_id`, `exception_type`, `severity` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), `financial_impact`, `priority_score` ($0-100$).
   - `suggested_owner`: `AP_CLERK`, `PROCUREMENT_BUYER`, `CONTROLLER`, `INTERNAL_AUDIT`.
   - `status`: `OPEN`, `AI_RECOMMENDED`, `HUMAN_REVIEW`, `RESOLVED`, `ESCALATED`.
   - `resolution_history`: Historical resolution statistics for identical anomaly types.

7. **`BankChangeAlert`**:
   - `vendor_id`, `old_fingerprint`, `new_fingerprint`, `days_since_change`, `affected_invoices`, `affected_payment_value`, `risk_severity`.
   - `controls`: Verification state for `independent_phone_verified`, `cfo_signoff`, `account_ownership_verified`, and `cooling_period_elapsed`.

8. **`CashPositionSummary` & `CashOutflowBucket`**:
   - Outflow buckets for $0-7\text{d}$, $8-14\text{d}$, $15-30\text{d}$, and $30+\text{d}$.
   - Breakdowns for `expected_outflow`, `approved_outflow`, `held_outflow`, `high_risk_outflow`, and `cash_at_risk`.

9. **`FinanceControlPolicy`**:
   - Configurable parameters: `po_tolerance_pct` (default $5.0\%$), `receipt_tolerance_pct` ($0.0\%$), `duplicate_similarity_threshold` ($0.85$), `bank_change_cooling_days` ($30$), `high_risk_amount_threshold` ($\$10,000.00$), `auto_resolve_minor_discrepancies` (`True`).

10. **`AuditEvent`**:
    - `event_id`, `timestamp`, `action`, `actor`, `affected_record`, `previous_state`, `new_state`, `reason`.

---

### 3.2 Deterministic Forensic & Reconciliation Engine (`backend/evidence.py`)

All mathematical and rule evaluations occur outside the LLM:

1. **Deterministic 3-Way Reconciliation**:
   - Matches Invoice against active PO and dock Goods Receipt (GRN).
   - Identifies:
     - Missing GRN dock receipts.
     - Partial deliveries ($\text{Qty}_{\text{Invoiced}} > \text{Qty}_{\text{Received}}$).
     - Overbilling against PO ($\text{Qty}_{\text{Invoiced}} > \text{Qty}_{\text{PO}}$).
     - Price markups ($\text{Unit Price}_{\text{Invoiced}} > \text{Unit Price}_{\text{PO}}$).
     - Unauthorized extra line items not present on approved POs.
     - Multiple invoices exhausting single PO balances.

2. **Two-Stage Hybrid Duplicate Engine**:
   - **Stage 1 (Candidate Generation Filter)**: Quickly identifies pairs with matching vendor IDs and near-match amounts within a 45-day window.
   - **Stage 2 (Weighted Similarity Function)**:
     $$\text{Score} = 0.25 \cdot S_{\text{inv\_no}} + 0.30 \cdot S_{\text{vendor}} + 0.25 \cdot S_{\text{amount}} + 0.10 \cdot S_{\text{date}} + 0.10 \cdot S_{\text{desc}}$$
   - **Distinct PO Protection Rule**: Invoices referencing distinct, valid PO numbers are protected from false-positive duplicate penalties.

3. **BEC Bank Account Fingerprint & Collusion Scan**:
   - Validates invoice remittance fingerprint against vendor master.
   - Enforces configurable cooling-off period (e.g. 30 days).
   - Detects **shared-bank collusion**: Flags unrelated vendors sharing the same bank routing fingerprint.

4. **Cross-Batch Structuring (Smurfing) Scan**:
   - Detects $\ge 3$ un-PO'd invoices from the same supplier within 5 days in the $\$8,000 - \$10,000$ band, linking them into an investigation cluster.

---

### 3.3 AI Controller & Citation Synthesis (`backend/agent.py`)

Synthesizes deterministic evidence into structured controller decisions:
- Mandatory structured JSON schema: `verdict`, `confidence`, `primary_reason`, `cited_evidence`, `recommended_action`, `next_best_action`, `requires_human_review`.
- **Refusal to Guess**: If deterministic evidence is missing, conflicting, or thin, the agent strictly outputs `requires_human_review = True` and refuses to guess.
- Does not perform financial arithmetic; all numbers, variances, and percentages are derived directly from the deterministic dossier.

---

### 3.4 Finance Operations Controller (`backend/controller.py`)

1. **Exception Prioritization Formula**:
   $$\text{Priority} = \min(100, \text{Base Severity} + \text{Impact Factor} + \text{Fraud Boost} + \text{Vendor Risk})$$
2. **Operational Ownership Assignment**:
   - 3-Way & Delivery Discrepancies $\rightarrow$ `PROCUREMENT_BUYER`
   - PO Variances & Duplicate Invoices $\rightarrow$ `AP_CLERK`
   - High-Value Holds & Cash Policy Violations $\rightarrow$ `CONTROLLER`
   - Structuring & BEC Bank Changes $\rightarrow$ `INTERNAL_AUDIT`
3. **Operational Issue Aggregation**: Groups multi-invoice anomalies by vendor and type (e.g., 4 structuring invoices consolidated into 1 operational ticket).
4. **Historical Resolution Reference**: Computes resolution trends from synthetic historical cases to recommend auto-resolution or escalation paths.
5. **Cash Position Forecasting**: Slices payables into maturity buckets and computes approved vs held exposure.
6. **BEC Dual-Control Payment Release Gate**: Automatically applies `PAYMENT_HOLD` and verifies 4 required controls before payment transition.

---

### 3.5 Centralized Audit Trail (`backend/audit.py`)

Maintains an in-memory chronological event log tracking:
- `BATCH_INGESTED`
- `CONTROL_PIPELINE_EXECUTED`
- `EXCEPTION_RESOLVED`
- `BANK_CONTROL_UPDATED`
- `VERDICT_OVERRIDE`
- `POLICY_UPDATED`

---

## 4. Synthetic Data Generation: 15 Core Scenarios (`backend/generator.py`)

The dataset generator produces 75 realistic records with balanced distributions:
1. **Clean 3-Way Matches**: Legitimate invoices matching PO lines and dock GRNs.
2. **Partial Goods Receipt**: Invoiced 50 units, dock received 25 units.
3. **Quantity Overbilled vs PO**: Invoiced 120 units against a 100-unit PO.
4. **Unit Price Markup**: Invoiced at $275.00/unit against approved $220.00/unit PO.
5. **Missing Goods Receipt (GRN)**: High-value physical goods invoiced with no dock scan.
6. **Extra Unapproved Line Item**: Invoice contains unapproved ancillary service charge.
7. **Multiple Invoices on Same PO**: Two distinct bills exhausting the same PO line.
8. **Business Email Compromise (BEC)**: Vendor bank fingerprint updated 2 days prior.
9. **Cross-Batch Structuring (Smurfing)**: 4 invoices of $9,500 each over 3 days ($38,000 total).
10. **Exact Duplicate Resubmission**: Same invoice submitted twice 4 days apart.
11. **Near Duplicate with Modified Number**: Same billing amount and vendor with altered ID.
12. **Shared Bank Account Collusion**: Multiple vendors sharing the same routing account.
13. **First-Time Unverified Vendor**: High-value invoice with no historical transactions.
14. **Overdue Invoices & Cash Exposure**: Invoices past due date impacting current cash position.
15. **Legitimate Recurring Bills with Distinct POs**: Monthly SaaS subscriptions sharing amounts but on distinct POs.

---

## 5. How to Run & Verify

```bash
# 1. Install dependencies
pip install fastapi uvicorn pydantic pytest tabulate

# 2. Run automated test suite
python -m pytest tests/ -v

# 3. Test synthetic generation & control metrics via CLI
python seed_data.py --seed 42 --size 75

# 4. Start the interactive Finance Control Center
python run.py
# Access dashboard at http://127.0.0.1:8000/
```

---

## 6. High-Impact Vectors for Future Enterprise Extension

When reviewing or extending Sentinel, consider these high-value engineering vectors:

### Vector A: Real-Time ERP & TMS Connectors
- Implement bi-directional connectors for **SAP S/4HANA (IDoc/OData)**, **Oracle NetSuite SuiteTalk**, and **Coupa AP** to ingest live PO, GRN, and vendor master feeds.

### Vector B: Multimodal Invoice Document Parsing
- Integrate **AWS Textract Queries** or **Azure Document Intelligence** to extract tabular line items, tax IDs, and remittance details directly from PDF/TIFF invoice scans.

### Vector C: Graph Neural Networks for Vendor Collusion Detection
- Model vendors, bank routing numbers, addresses, and phone numbers in a graph database (Neo4j / Amazon Neptune) to detect multi-entity shell company collusion.

### Vector D: Automated Treasury & Payment Rail Integration
- Connect payment release webhooks directly to corporate banking APIs (e.g., J.P. Morgan PayConnexion or Stripe Treasury) for automated release upon dual-control authorization.
