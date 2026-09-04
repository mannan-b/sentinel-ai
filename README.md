# 🛡️ Sentinel — AP Fraud & Duplicate-Payment Control Agent

**Sentinel** is an autonomous Accounts Payable (AP) financial control agent designed to review batches of vendor invoices like an elite forensic auditor. Rather than classifying invoices in isolation, Sentinel gathers a **deterministic, 5-pillar structured evidence dossier** (PO match & tolerance, bank routing change history, cross-batch duplicate detection, new-vendor anomalies, and cross-batch multi-invoice structuring scans) and renders transparent, fact-cited verdicts.

---

## ⚡ Quick Start (Runnable Local Demo)

### 1. Requirements
- Python 3.10+
- Installed packages: `fastapi`, `uvicorn`, `pydantic`

```bash
pip install fastapi uvicorn pydantic
```

### 2. Generate / Seed Synthetic Data (CLI Inspection)
To generate and score deterministic batches via the CLI:
```bash
python seed_data.py --seed 42 --size 75
```

### 3. Launch Sentinel Web Server
```bash
python run.py
```

### 4. Open Interactive Dashboard
Open your browser to: **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

---

## 🌟 Key Features & Architectural Capabilities

### 1. 🔍 5-Pillar Structured Evidence Layer (Deterministic & Zero-Hallucination)
Before any verdict is rendered, Sentinel extracts structured evidence for every invoice in batch context:
1. **PO Match & Tolerance Check**: Validates PO existence, approved amount, and variance percentage against policy tolerance (5%).
2. **Bank Account & BEC History**: Detects recent bank routing changes (< 30 days) and unverified first-time account mismatches.
3. **Cross-Batch Duplicate Detection**: Pinpoints exact resubmissions and near-duplicates (same vendor + amount within tight date windows) while preserving the original legitimate invoice.
4. **Vendor Historical Anomaly Scan**: Identifies first-time vendors submitting high-value un-PO'd bills.
5. **Cross-Batch Structuring (Smurfing) Scan**: Cross-invoice reasoning across the entire batch to detect evasive split invoices.

### 2. 🎯 The Four AP Verdicts
- **Auto-Approve (`auto_approve`)**: Clean 3-way match, verified bank fingerprint, zero duplicate collisions.
- **Hold for Review (`hold_for_review`)**: Missing PO, tolerance overages, or unverified new vendors — *the system explicitly refuses to guess when evidence is thin*.
- **Escalate Fraud (`escalate_fraud`)**: High-risk compromised bank accounts (BEC) or cross-batch structuring evasion.
- **Reject Duplicate (`reject_duplicate`)**: Matched duplicate invoice resubmissions with exact collision pointers.

> **Non-Negotiable Rule:** Every non-approval verdict strictly cites real evidence fields from the dossier — no bare confidence numbers without reasoning.

### 3. 🚨 Flagship Demo Moment: Cross-Invoice Structuring Caught
- **The Attack:** *Apex Security & Guarding LLC* split a single **$38,000.00** obligation into **4 invoices of $9,500.00 each** (submitted within 3 days without PO) to intentionally hover right beneath the **$10,000.00 single-invoice approval threshold**.
- **The Detection:** Single-row classifiers miss this completely because each $9,500 invoice appears unremarkable in isolation. Sentinel groups vendor commitments across the batch, flags the entire cluster, cites the cumulative total, and escalates all 4 invoices to Fraud Risk.

---

## 📊 Evaluation Scorecard vs Ground Truth (Seed 42)

| Metric | Fraud Risk Detection | Duplicate Rejection | Operational Control |
| :--- | :---: | :---: | :---: |
| **Precision** | **100.0%** (5 / 5) | **100.0%** (2 / 2) | — |
| **Recall** | **100.0%** (5 / 5) | **100.0%** (2 / 2) | — |
| **F1 Score** | **1.000** | **1.000** | — |
| **False Positives on Clean Vendors** | **0** | **0** | **0 Cost Impact** |
| **Auto-Resolved Rate** | — | — | **94.7%** |
| **Routed to Human Review** | — | — | **5.3%** (Refusal Path) |
| **Avg Cited Facts per Flag** | — | — | **3.2 facts / decision** |

---

## 🖥️ Web UI Layout

- **Run View & Ingestion Visualizer**: Seed selector (1-99999), batch size (50-100), and animated multi-step agent execution.
- **Results Dashboard**: KPI summary cards, filter pills (`All`, `Auto-Approve`, `Duplicates`, `Fraud Risks`, `Hold for Review`, `Structuring Cluster`), and searchable invoice table with expandable cited facts.
- **Evidence Dossier Modal**: Deep-dive inspector displaying all 5 evidence pillars, cited fact paths, and Human-in-the-Loop AP override controls.
- **Scoring & Metrics Lab**: Real-time confusion matrix, precision/recall/F1 metrics, and auto-resolution efficiency gauges.
- **Flagship Structuring Breakdown**: Dedicated visual flow showing the split $9,500 invoices vs the evaded $10k threshold.

---

## 📁 Repository Structure

```
├── backend/
│   ├── __init__.py
│   ├── models.py            # Pydantic models for Invoices, POs, Evidence Dossiers, Verdicts, Scorecard
│   ├── generator.py         # Deterministic synthetic data generator with engineered AP fraud patterns
│   ├── evidence.py          # Deterministic 5-pillar structured evidence gathering layer
│   ├── agent.py             # Sentinel AP Verdict Agent with zero-hallucination citation engine
│   ├── metrics.py           # Evaluation engine calculating precision, recall, F1, and auto-resolution rates
│   └── server.py            # FastAPI REST API & static file backend
├── frontend/
│   ├── index.html           # Dark-mode single page dashboard UI
│   ├── style.css            # Custom CSS with glassmorphism & micro-animations
│   └── app.js               # Reactive vanilla JS frontend
├── tests/
│   ├── test_pipeline.py     # Automated end-to-end pipeline test suite
│   └── debug_pipeline.py    # Diagnostic script
├── seed_data.py             # CLI generation & evaluation utility
├── run.py                   # Master application runner
└── README.md                # Documentation
```
