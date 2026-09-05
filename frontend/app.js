// Sentinel AI Finance Controller Application
document.addEventListener("DOMContentLoaded", () => {
  let batchData = {
    seed: 42,
    is_analyzed: false,
    invoices: [],
    scorecard: null,
    cash_position: null,
    exceptions: [],
    exception_groups: [],
    bank_alerts: [],
    policy: null,
    vendors: [],
    purchase_orders: [],
    goods_receipts: []
  };

  let currentFilter = "ALL";
  let currentExFilter = "ALL";
  let searchQuery = "";
  let activeInvoiceId = null;
  let activeExceptionId = null;

  // DOM Elements
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabContents = document.querySelectorAll(".tab-content");
  
  const btnGenerate = document.getElementById("btnGenerate");
  const btnAnalyze = document.getElementById("btnAnalyze");
  const batchSeedInput = document.getElementById("batchSeed");
  const batchSizeSelect = document.getElementById("batchSize");

  const searchInput = document.getElementById("searchInput");
  const filterPills = document.querySelectorAll(".filter-pill[data-filter]");
  const exFilterPills = document.querySelectorAll(".filter-pill[data-ex-filter]");
  const invoicesTableBody = document.getElementById("invoicesTableBody");
  const exceptionsTableBody = document.getElementById("exceptionsTableBody");
  const exceptionGroupsGrid = document.getElementById("exceptionGroupsGrid");
  const paymentScheduleBody = document.getElementById("paymentScheduleBody");
  const auditTrailBody = document.getElementById("auditTrailBody");
  const becChecklistGrid = document.getElementById("becChecklistGrid");
  const structuringFlowGrid = document.getElementById("structuringFlowGrid");
  const outflowBucketsGrid = document.getElementById("outflowBucketsGrid");

  // KPI elements
  const kpiTotal = document.getElementById("kpiTotal");
  const kpiSTPRate = document.getElementById("kpiSTPRate");
  const kpiSTPCount = document.getElementById("kpiSTPCount");
  const kpiApproved = document.getElementById("kpiApproved");
  const kpiMatchRate = document.getElementById("kpiMatchRate");
  const kpiApprovedAmount = document.getElementById("kpiApprovedAmount");
  const kpiExceptionsCount = document.getElementById("kpiExceptionsCount");
  const kpiBlockedAmount = document.getElementById("kpiBlockedAmount");
  const kpiCashAtRisk = document.getElementById("kpiCashAtRisk");
  const kpiDuplicatePrevented = document.getElementById("kpiDuplicatePrevented");
  const tabCountExceptions = document.getElementById("tabCountExceptions");

  // Counts
  const countAll = document.getElementById("countAll");
  const countApprove = document.getElementById("countApprove");
  const countDup = document.getElementById("countDup");
  const countFraud = document.getElementById("countFraud");
  const countReview = document.getElementById("countReview");

  // Payment Queue KPI elements
  const qReadyAmount = document.getElementById("qReadyAmount");
  const qReadyCount = document.getElementById("qReadyCount");
  const qReconcileAmount = document.getElementById("qReconcileAmount");
  const qReconcileCount = document.getElementById("qReconcileCount");
  const qDocAmount = document.getElementById("qDocAmount");
  const qDocCount = document.getElementById("qDocCount");
  const qFraudAmount = document.getElementById("qFraudAmount");
  const qFraudCount = document.getElementById("qFraudCount");
  const qDupAmount = document.getElementById("qDupAmount");
  const qDupCount = document.getElementById("qDupCount");

  // Dossier Modal elements
  const dossierModal = document.getElementById("dossierModal");
  const btnCloseModal = document.getElementById("btnCloseModal");
  const modalInvoiceId = document.getElementById("modalInvoiceId");
  const modalVendorName = document.getElementById("modalVendorName");
  const modalVerdictBox = document.getElementById("modalVerdictBox");
  const modalVerdictTag = document.getElementById("modalVerdictTag");
  const modalConfidence = document.getElementById("modalConfidence");
  const modalPrimaryReason = document.getElementById("modalPrimaryReason");
  const modalAction = document.getElementById("modalAction");
  const modalNextAction = document.getElementById("modalNextAction");
  const modalCitedEvidenceList = document.getElementById("modalCitedEvidenceList");

  const pillarPO = document.getElementById("pillarPO");
  const pillarGRN = document.getElementById("pillarGRN");
  const pillarBank = document.getElementById("pillarBank");
  const pillarDup = document.getElementById("pillarDup");
  const pillarStructuring = document.getElementById("pillarStructuring");

  const overrideVerdictSelect = document.getElementById("overrideVerdictSelect");
  const overrideNotes = document.getElementById("overrideNotes");
  const btnSubmitOverride = document.getElementById("btnSubmitOverride");

  const btnOpenWhyFromDossier = document.getElementById("btnOpenWhyFromDossier");
  const btnReleasePaymentFromDossier = document.getElementById("btnReleasePaymentFromDossier");
  const paymentReleaseFeedback = document.getElementById("paymentReleaseFeedback");

  // Exception Action Modal
  const exceptionModal = document.getElementById("exceptionModal");
  const btnCloseExceptionModal = document.getElementById("btnCloseExceptionModal");
  const modalExceptionId = document.getElementById("modalExceptionId");
  const modalExceptionDetails = document.getElementById("modalExceptionDetails");
  const exceptionActionSelect = document.getElementById("exceptionActionSelect");
  const modalGrnReference = document.getElementById("modalGrnReference");
  const modalReceivedQty = document.getElementById("modalReceivedQty");
  const exceptionResolutionNotes = document.getElementById("exceptionResolutionNotes");
  const btnSubmitExceptionResolution = document.getElementById("btnSubmitExceptionResolution");

  // Why Traceability Modal
  const whyModal = document.getElementById("whyModal");
  const btnCloseWhyModal = document.getElementById("btnCloseWhyModal");
  const whyModalTitle = document.getElementById("whyModalTitle");
  const whyModalSummary = document.getElementById("whyModalSummary");
  const whyBlockingReasons = document.getElementById("whyBlockingReasons");
  const whyReconcileFindings = document.getElementById("whyReconcileFindings");
  const whyFraudFindings = document.getElementById("whyFraudFindings");
  const whyCashAtRisk = document.getElementById("whyCashAtRisk");
  const whyActionOwner = document.getElementById("whyActionOwner");

  // Audit tab elements
  const btnVerifyAuditChain = document.getElementById("btnVerifyAuditChain");
  const auditChainStatusBadge = document.getElementById("auditChainStatusBadge");

  // Policy Modal
  const policyModal = document.getElementById("policyModal");
  const btnOpenPolicy = document.getElementById("btnOpenPolicy");
  const btnClosePolicy = document.getElementById("btnClosePolicy");
  const btnSavePolicy = document.getElementById("btnSavePolicy");
  const policyPOTolerance = document.getElementById("policyPOTolerance");
  const policyApprovalThreshold = document.getElementById("policyApprovalThreshold");
  const policyDupThreshold = document.getElementById("policyDupThreshold");
  const policyBankCooling = document.getElementById("policyBankCooling");

  // Progress overlay
  const analysisOverlay = document.getElementById("analysisOverlay");
  const analysisProgressBar = document.getElementById("analysisProgressBar");
  const analysisStatusText = document.getElementById("analysisStatusText");

  // Tab switching
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      tabBtns.forEach(b => b.classList.remove("active"));
      tabContents.forEach(c => c.classList.remove("active"));
      
      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      const targetContent = document.getElementById(targetId);
      if (targetContent) targetContent.classList.add("active");

      if (targetId === "tab-audit") loadAuditTrail();
    });
  });

  // Filter pills (Invoices)
  filterPills.forEach(pill => {
    pill.addEventListener("click", () => {
      filterPills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      currentFilter = pill.getAttribute("data-filter");
      renderInvoicesTable();
    });
  });

  // Filter pills (Exceptions)
  exFilterPills.forEach(pill => {
    pill.addEventListener("click", () => {
      exFilterPills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      currentExFilter = pill.getAttribute("data-ex-filter");
      renderExceptionsTable();
    });
  });

  // Search input
  searchInput.addEventListener("input", (e) => {
    searchQuery = e.target.value.toLowerCase().trim();
    renderInvoicesTable();
  });

  // Batch Generation
  btnGenerate.addEventListener("click", async () => {
    const seed = parseInt(batchSeedInput.value) || 42;
    const size = parseInt(batchSizeSelect.value) || 75;
    
    try {
      btnGenerate.disabled = true;
      btnGenerate.textContent = "Generating...";
      const res = await fetch("/api/batch/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ seed, size })
      });
      if (!res.ok) throw new Error("Failed to generate batch");
      await loadLatestBatch();
    } catch (err) {
      alert("Error generating batch: " + err.message);
    } finally {
      btnGenerate.disabled = false;
      btnGenerate.innerHTML = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg> Generate Batch`;
    }
  });

  // Batch Analysis Pipeline Execution with Real Step Visualizer
  btnAnalyze.addEventListener("click", async () => {
    try {
      btnAnalyze.disabled = true;
      showProgress(15, "1/6 Ingesting AP Invoice Batch & PO Registry...");
      
      await new Promise(r => setTimeout(r, 200));
      showProgress(35, "2/6 Executing Deterministic 3-Way Reconciliation (Invoice ↔ PO ↔ GRN)...");

      await new Promise(r => setTimeout(r, 200));
      showProgress(55, "3/6 Running Hybrid Duplicate Scan & Cross-Batch Structuring Matrix...");

      await new Promise(r => setTimeout(r, 200));
      showProgress(75, "4/6 Synthesizing Evidence-Grounded AI Controller Verdicts...");

      await new Promise(r => setTimeout(r, 150));
      showProgress(90, "5/6 Updating Payment Queue & AP Cash Outflow Forecast...");

      const res = await fetch("/api/batch/analyze", { method: "POST" });
      if (!res.ok) throw new Error("Analysis failed");

      showProgress(100, "6/6 Control Run Complete. Ledger Updated.");
      await new Promise(r => setTimeout(r, 200));
      hideProgress();

      await loadLatestBatch();
    } catch (err) {
      hideProgress();
      alert("Error running control pipeline: " + err.message);
    } finally {
      btnAnalyze.disabled = false;
    }
  });

  function showProgress(pct, msg) {
    analysisOverlay.classList.remove("hidden");
    analysisProgressBar.style.width = `${pct}%`;
    analysisStatusText.textContent = msg;
  }

  function hideProgress() {
    analysisOverlay.classList.add("hidden");
  }

  // Format Helpers
  function formatUSD(amount) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(amount || 0);
  }

  // Fetch Latest Batch Data
  async function loadLatestBatch() {
    try {
      const res = await fetch("/api/batch/latest");
      if (!res.ok) throw new Error("Failed to load batch data");
      const data = await res.json();
      batchData = data;
      renderDashboard();
    } catch (err) {
      console.error("Load batch error:", err);
    }
  }

  // Render Dashboard
  function renderDashboard() {
    const sc = batchData.scorecard;
    const cp = batchData.cash_position;
    if (!sc) return;

    // Top KPIs
    kpiTotal.textContent = sc.total_invoices;
    kpiMatchRate.textContent = `${sc.reconciliation_match_rate}% 3-Way Match Rate`;
    
    if (kpiSTPRate) kpiSTPRate.textContent = `${sc.stp_rate}%`;
    if (kpiSTPCount) kpiSTPCount.textContent = `${sc.stp_count} Auto-Cleared (No Human)`;

    kpiApproved.textContent = sc.auto_approved_count;
    kpiApprovedAmount.textContent = `${formatUSD(cp ? cp.total_approved_payable : 0)} Approved`;

    kpiExceptionsCount.textContent = sc.total_exceptions_count;
    kpiBlockedAmount.textContent = `${formatUSD(sc.payment_value_blocked)} Held / Under Review`;

    kpiCashAtRisk.textContent = formatUSD(sc.cash_currently_at_risk);
    kpiDuplicatePrevented.textContent = formatUSD(sc.duplicate_value_prevented);
    tabCountExceptions.textContent = sc.total_exceptions_count;

    // Filter Counts
    countAll.textContent = sc.total_invoices;
    countApprove.textContent = sc.auto_approved_count;
    countDup.textContent = sc.reject_duplicate_count;
    countFraud.textContent = sc.escalate_fraud_count;
    countReview.textContent = sc.held_for_review_count;

    // Payment Queue Summary
    if (cp) {
      qReadyAmount.textContent = formatUSD(cp.total_approved_payable);
      qReadyCount.textContent = `${sc.auto_approved_count} Approved for Disbursement`;

      qReconcileAmount.textContent = formatUSD(sc.payment_value_blocked * 0.4);
      qReconcileCount.textContent = "Price/Quantity Overages Blocked";

      qDocAmount.textContent = formatUSD(sc.payment_value_blocked * 0.6);
      qDocCount.textContent = "Awaiting Warehouse Dock GRNs";

      qFraudAmount.textContent = formatUSD(cp.total_fraud_risk_payable);
      qFraudCount.textContent = `${sc.escalate_fraud_count} Fraud & BEC Holds`;

      qDupAmount.textContent = formatUSD(cp.total_duplicate_prevented);
      qDupCount.textContent = `${sc.reject_duplicate_count} Duplicate Copies Rejected`;

      renderCashOutflowWidget(cp);
      renderPaymentScheduleTable(cp);
    }

    // Scorecard & Metrics Lab
    document.getElementById("metricMatchRate").textContent = `${sc.reconciliation_match_rate}%`;
    document.getElementById("metricAutoRate").textContent = `${sc.auto_approved_pct}%`;
    document.getElementById("metricHumanRate").textContent = `${sc.human_routing_pct}%`;
    document.getElementById("metricAvgCitations").textContent = `${sc.avg_evidence_citations_per_non_approval.toFixed(1)} facts / flag`;

    document.getElementById("metricFraudPrec").textContent = `${(sc.fraud_metrics.precision * 100).toFixed(1)}%`;
    document.getElementById("metricFraudRecall").textContent = `${(sc.fraud_metrics.recall * 100).toFixed(1)}%`;
    document.getElementById("metricFraudF1").textContent = sc.fraud_metrics.f1_score.toFixed(3);
    document.getElementById("metricFraudTP").textContent = sc.fraud_metrics.true_positives;
    document.getElementById("metricFraudFP").textContent = sc.fraud_metrics.false_positives;
    document.getElementById("metricFraudFN").textContent = sc.fraud_metrics.false_negatives;

    document.getElementById("metricDupPrec").textContent = `${(sc.duplicate_metrics.precision * 100).toFixed(1)}%`;
    document.getElementById("metricDupRecall").textContent = `${(sc.duplicate_metrics.recall * 100).toFixed(1)}%`;
    document.getElementById("metricDupF1").textContent = sc.duplicate_metrics.f1_score.toFixed(3);
    document.getElementById("metricDupTP").textContent = sc.duplicate_metrics.true_positives;
    document.getElementById("metricDupFP").textContent = sc.duplicate_metrics.false_positives;
    document.getElementById("metricDupFN").textContent = sc.duplicate_metrics.false_negatives;

    // Render Sub-Views
    renderInvoicesTable();
    renderExceptionsTable();
    renderExceptionGroups();
    renderBECControls();
    renderStructuringFlow(sc.structuring_flagship);
  }

  // Render Outflow Forecast Widget
  function renderCashOutflowWidget(cp) {
    outflowBucketsGrid.innerHTML = "";
    cp.outflow_forecast.forEach(b => {
      const card = document.createElement("div");
      card.className = "outflow-bucket-card";
      card.innerHTML = `
        <div class="bucket-title">${b.days_range}</div>
        <div class="bucket-total">${formatUSD(b.total_projected_outflow)}</div>
        <div class="bucket-breakdown">
          <div class="breakdown-row"><span>Approved:</span> <strong class="text-emerald">${formatUSD(b.approved_amount)}</strong></div>
          <div class="breakdown-row"><span>Held (Review):</span> <strong class="text-amber">${formatUSD(b.held_amount)}</strong></div>
          <div class="breakdown-row"><span>High Risk / BEC:</span> <strong class="text-rose">${formatUSD(b.high_risk_amount)}</strong></div>
        </div>
      `;
      outflowBucketsGrid.appendChild(card);
    });
  }

  // Render Payment Schedule Table
  function renderPaymentScheduleTable(cp) {
    paymentScheduleBody.innerHTML = "";
    cp.outflow_forecast.forEach(b => {
      const tr = document.createElement("tr");
      const riskLevel = b.high_risk_amount > 0 ? `<span class="badge badge-fraud">HIGH RISK BLOCKED</span>` : (b.held_amount > 0 ? `<span class="badge badge-hold">REVIEW PENDING</span>` : `<span class="badge badge-approved">CLEAN OUTFLOW</span>`);
      tr.innerHTML = `
        <td style="font-weight:700; color:#fff;">${b.days_range}</td>
        <td class="text-emerald" style="font-family:'JetBrains Mono'; font-weight:700;">${formatUSD(b.approved_amount)}</td>
        <td class="text-amber" style="font-family:'JetBrains Mono'; font-weight:600;">${formatUSD(b.held_amount)}</td>
        <td class="text-rose" style="font-family:'JetBrains Mono'; font-weight:600;">${formatUSD(b.high_risk_amount)}</td>
        <td style="font-family:'JetBrains Mono'; font-weight:800; color:#fff;">${formatUSD(b.total_projected_outflow)}</td>
        <td>${riskLevel}</td>
      `;
      paymentScheduleBody.appendChild(tr);
    });
  }

  // Filter logic for Invoices
  function matchesInvoiceFilter(item) {
    const v = item.verdict ? item.verdict.verdict : "";
    const isStructuring = item.dossier && item.dossier.structuring_evidence && item.dossier.structuring_evidence.in_structuring_cluster;

    if (currentFilter === "ALL") {
      // pass
    } else if (currentFilter === "STRUCTURING") {
      if (!isStructuring) return false;
    } else if (currentFilter !== v) {
      return false;
    }

    if (searchQuery) {
      const id = item.invoice.invoice_id.toLowerCase();
      const vendor = item.invoice.vendor_name.toLowerCase();
      const po = (item.invoice.po_reference || "").toLowerCase();
      const reason = item.verdict ? item.verdict.primary_reason.toLowerCase() : "";
      
      if (!id.includes(searchQuery) && !vendor.includes(searchQuery) && !po.includes(searchQuery) && !reason.includes(searchQuery)) {
        return false;
      }
    }
    return true;
  }

  // Render Invoices Table
  function renderInvoicesTable() {
    invoicesTableBody.innerHTML = "";
    const filtered = batchData.invoices.filter(matchesInvoiceFilter);

    if (filtered.length === 0) {
      invoicesTableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:32px; color:#64748b;">No invoices matching the current filter.</td></tr>`;
      return;
    }

    filtered.forEach(item => {
      const inv = item.invoice;
      const v = item.verdict;
      const d = item.dossier;

      // Verdict badge
      let badgeHtml = `<span class="badge badge-neutral">PENDING</span>`;
      if (v) {
        if (v.verdict === "auto_approve") badgeHtml = `<span class="badge badge-approved">✓ Auto-Approve</span>`;
        else if (v.verdict === "reject_duplicate") badgeHtml = `<span class="badge badge-dup">✕ Reject (Duplicate)</span>`;
        else if (v.verdict === "escalate_fraud") badgeHtml = `<span class="badge badge-fraud">⚠ Escalate (Fraud)</span>`;
        else if (v.verdict === "hold_for_review") badgeHtml = `<span class="badge badge-hold">? Hold for Review</span>`;
      }

      // 3-Way Match badge
      let matchBadge = `<span style="color:#64748b;">No PO</span>`;
      if (d && d.receipt_evidence) {
        const rStatus = d.receipt_evidence.match_status;
        if (rStatus === "EXACT_3WAY_MATCH") matchBadge = `<span class="badge badge-approved">✓ 3-Way Match</span>`;
        else if (rStatus === "MISSING_GRN") matchBadge = `<span class="badge badge-hold">Missing GRN</span>`;
        else if (rStatus === "QUANTITY_OVERBILLED") matchBadge = `<span class="badge badge-hold">Qty Overbilled</span>`;
        else if (rStatus === "PRICE_MISMATCH") matchBadge = `<span class="badge badge-hold">Price Mismatch</span>`;
        else if (rStatus === "EXTRA_LINE_ITEM") matchBadge = `<span class="badge badge-hold">Extra Line Item</span>`;
        else matchBadge = `<span class="badge badge-neutral">${rStatus}</span>`;
      }

      // Payment Status badge
      let paymentBadge = `<span class="badge badge-neutral">${inv.payment_status}</span>`;
      if (inv.payment_status === "RELEASED") paymentBadge = `<span class="badge badge-approved" style="background:#059669; color:#fff;">✓ RELEASED</span>`;
      else if (inv.payment_status === "READY_FOR_PAYMENT") paymentBadge = `<span class="badge badge-approved">READY</span>`;
      else if (inv.payment_status === "FRAUD_HOLD" || inv.payment_status === "PAYMENT_HOLD") paymentBadge = `<span class="badge badge-fraud">HOLD</span>`;
      else if (inv.payment_status === "BLOCKED_BY_RECONCILIATION" || inv.payment_status === "MISSING_DOCUMENTATION") paymentBadge = `<span class="badge badge-hold">BLOCKED</span>`;
      else if (inv.payment_status === "DUPLICATE_REJECTED") paymentBadge = `<span class="badge badge-dup">REJECTED</span>`;

      // Inline facts / highlights
      let factBadges = "";
      if (d) {
        if (d.structuring_evidence.in_structuring_cluster) {
          factBadges += `<span class="badge badge-fraud" style="margin-right:4px;">Structuring Cluster</span>`;
        }
        if (d.bank_evidence.risk_level === "HIGH_RISK_RECENT_CHANGE") {
          factBadges += `<span class="badge badge-fraud" style="margin-right:4px;">BEC Bank Change</span>`;
        }
        if (d.duplicate_evidence.is_duplicate_risk) {
          factBadges += `<span class="badge badge-dup" style="margin-right:4px;">${d.duplicate_evidence.candidates[0] ? (d.duplicate_evidence.candidates[0].similarity_score * 100).toFixed(0) : 0}% Match</span>`;
        }
      }

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="inv-id-cell">${inv.invoice_id}</td>
        <td>
          <div style="font-weight:600; color:#f8fafc;">${inv.vendor_name}</div>
          <div style="font-size:0.75rem; color:#64748b;">${inv.vendor_id}</div>
        </td>
        <td class="amount-cell">${formatUSD(inv.amount)}</td>
        <td>${matchBadge}</td>
        <td>${badgeHtml}</td>
        <td>${paymentBadge}</td>
        <td>
          <div>${factBadges || (v ? v.primary_reason.slice(0, 48) + '...' : '--')}</div>
          <div style="font-size:0.72rem; color:#64748b; margin-top:2px;">Due: ${inv.due_date} (${inv.payment_terms})</div>
        </td>
        <td>
          <div style="display:flex; gap:6px;">
            <button class="btn btn-secondary" style="padding:4px 8px; font-size:0.75rem;" onclick="window.sentinelOpenWhy('${inv.invoice_id}')">
              🔍 Why?
            </button>
            <button class="btn btn-secondary" style="padding:4px 8px; font-size:0.75rem;" onclick="window.sentinelOpenDossier('${inv.invoice_id}')">
              Dossier →
            </button>
          </div>
        </td>
      `;
      invoicesTableBody.appendChild(tr);
    });
  }

  // Render Exceptions Workbench Table
  function renderExceptionsTable() {
    exceptionsTableBody.innerHTML = "";
    
    let filteredEx = batchData.exceptions;
    if (currentExFilter === "RESOLVED") {
      filteredEx = filteredEx.filter(e => e.status === "RESOLVED");
    } else if (currentExFilter !== "ALL") {
      filteredEx = filteredEx.filter(e => e.severity === currentExFilter && e.status !== "RESOLVED");
    }

    if (filteredEx.length === 0) {
      exceptionsTableBody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding:24px; color:#64748b;">No exceptions matching severity filter '${currentExFilter}'.</td></tr>`;
      return;
    }

    filteredEx.forEach(ex => {
      let sevBadge = `<span class="badge badge-hold">${ex.severity}</span>`;
      if (ex.severity === "CRITICAL") sevBadge = `<span class="badge badge-fraud">CRITICAL</span>`;
      else if (ex.severity === "HIGH") sevBadge = `<span class="badge badge-dup">HIGH</span>`;

      let statusBadge = `<span class="badge badge-neutral">${ex.status}</span>`;
      if (ex.status === "RESOLVED") statusBadge = `<span class="badge badge-approved">RESOLVED</span>`;
      else if (ex.status === "ESCALATED") statusBadge = `<span class="badge badge-fraud">ESCALATED</span>`;

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td style="font-family:'JetBrains Mono'; font-weight:800; color:#fb7185;">${ex.priority_score.toFixed(1)}</td>
        <td class="inv-id-cell">${ex.exception_id}</td>
        <td>
          <div style="font-weight:600; color:#f8fafc;">${ex.vendor_name}</div>
          <div style="font-size:0.74rem; color:#64748b;">Inv: ${ex.invoice_id}</div>
        </td>
        <td><span class="badge badge-neutral">${ex.exception_type}</span></td>
        <td style="font-family:'JetBrains Mono'; font-weight:700; color:#fff;">${formatUSD(ex.financial_impact)}</td>
        <td>
          <div style="font-size:0.82rem; color:#f1f5f9; margin-bottom:4px;">${ex.evidence_summary}</div>
          <div style="font-size:0.76rem; color:#818cf8;"><strong>Action:</strong> ${ex.recommended_action}</div>
        </td>
        <td><span class="badge badge-neutral">${ex.suggested_owner}</span></td>
        <td>${statusBadge}</td>
        <td>
          ${ex.status !== "RESOLVED" ? `
            <button class="btn btn-secondary" style="padding:4px 8px; font-size:0.75rem;" onclick="window.sentinelOpenExceptionAction('${ex.exception_id}')">
              Action →
            </button>
          ` : `<span style="font-size:0.75rem; color:#10b981;">✓ Handled</span>`}
        </td>
      `;
      exceptionsTableBody.appendChild(tr);
    });
  }

  // Render Exception Groups Banner
  function renderExceptionGroups() {
    exceptionGroupsGrid.innerHTML = "";
    batchData.exception_groups.slice(0, 4).forEach(g => {
      const card = document.createElement("div");
      card.className = "group-card";
      card.innerHTML = `
        <div class="group-head">
          <span class="group-title">${g.title}</span>
          <span class="badge badge-fraud">${g.severity}</span>
        </div>
        <div class="group-impact">${formatUSD(g.total_financial_impact)} Total Exposure</div>
        <div class="group-pattern">${g.pattern_summary}</div>
        <button class="btn btn-secondary" style="width:100%; font-size:0.76rem; padding:4px 8px;" onclick="window.sentinelFilterByVendor('${g.vendor_name}')">
          View ${g.invoice_count} Group Invoices →
        </button>
      `;
      exceptionGroupsGrid.appendChild(card);
    });
  }

  // Render BEC Bank Controls
  function renderBECControls() {
    becChecklistGrid.innerHTML = "";
    if (!batchData.bank_alerts || batchData.bank_alerts.length === 0) {
      becChecklistGrid.innerHTML = `<div style="color:#64748b;">No active bank change alerts in current batch.</div>`;
      return;
    }

    const alertItem = batchData.bank_alerts[0];
    const coolingTarget = batchData.policy ? batchData.policy.bank_cooling_days : 30;
    const controls = [
      { key: "independent_phone_verified", label: "1. Out-of-Band Verbal Callback", sub: "Verified with CFO over verified phone number", status: alertItem.independent_phone_verified },
      { key: "cfo_signoff", label: "2. Controller / CFO Dual-Signoff", sub: "Formal signoff on bank modification record", status: alertItem.cfo_signoff },
      { key: "account_ownership_verified", label: "3. Account Ownership & Void Check", sub: "Verified bank letter / void check on file", status: alertItem.account_ownership_verified },
      { key: "cooling_period_elapsed", label: "4. Cooling Period Compliance", sub: `${alertItem.days_since_change} of ${coolingTarget} days elapsed (Deterministic Security Gate)`, status: alertItem.cooling_period_elapsed }
    ];

    controls.forEach(c => {
      const isPass = (c.status === "VERIFIED");
      const box = document.createElement("div");
      box.className = "bec-control-item";
      box.innerHTML = `
        <div>
          <div class="bec-item-title">${c.label}</div>
          <div class="bec-item-sub">${c.sub}</div>
        </div>
        <div>
          <span class="badge ${isPass ? 'badge-approved' : 'badge-hold'}" style="margin-bottom:8px; display:inline-block;">${c.status}</span>
          ${!isPass ? `
            <button class="btn btn-secondary" style="width:100%; font-size:0.75rem; padding:4px 8px;" onclick="window.sentinelVerifyBankControl('${alertItem.vendor_id}', '${c.key}')">
              Verify & Approve
            </button>
          ` : `<div style="font-size:0.74rem; color:#10b981;">✓ Verified by Officer</div>`}
        </div>
      `;
      becChecklistGrid.appendChild(box);
    });
  }

  // Verify bank control handler
  window.sentinelVerifyBankControl = async function(vendorId, controlKey) {
    try {
      const res = await fetch(`/api/bank-controls/${vendorId}/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ control_name: controlKey, status: "VERIFIED", notes: "Officer manual verification on dashboard" })
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Verification failed");
      }
      await loadLatestBatch();
    } catch (err) {
      alert("Bank Control Error: " + err.message);
    }
  };

  // Render Structuring Visual Flow
  function renderStructuringFlow(flagship) {
    structuringFlowGrid.innerHTML = "";
    if (!flagship || !flagship.detected) return;

    flagship.cluster_invoice_ids.forEach((id, idx) => {
      const item = batchData.invoices.find(i => i.invoice.invoice_id === id);
      if (!item) return;

      const card = document.createElement("div");
      card.className = "struct-flow-card";
      card.innerHTML = `
        <div class="card-head">
          <span class="inv-id-cell">${item.invoice.invoice_id}</span>
          <span class="badge badge-fraud">Installment #${idx + 1}</span>
        </div>
        <div class="card-amount">${formatUSD(item.invoice.amount)}</div>
        <div class="card-limit-check">⚠️ $500 below $10,000 threshold</div>
        <p style="font-size:0.78rem; color:#94a3b8; margin-bottom:12px;">${item.invoice.line_items_summary}</p>
        <div style="font-size:0.75rem; color:#64748b;">Date: ${item.invoice.invoice_date} | Terms: ${item.invoice.payment_terms} | No PO</div>
        <button class="btn btn-secondary" style="margin-top:10px; width:100%; font-size:0.78rem; padding:6px 10px;" onclick="window.sentinelOpenDossier('${id}')">
          View Complete Dossier
        </button>
      `;
      structuringFlowGrid.appendChild(card);
    });
  }

  // Load Audit Trail Stream
  async function loadAuditTrail() {
    try {
      const res = await fetch("/api/audit-trail");
      if (!res.ok) throw new Error("Could not fetch audit trail");
      const data = await res.json();
      
      if (auditChainStatusBadge) {
        if (data.chain_integrity_valid) {
          auditChainStatusBadge.className = "badge badge-approved";
          auditChainStatusBadge.textContent = "✓ SHA-256 Chain Intact";
        } else {
          auditChainStatusBadge.className = "badge badge-fraud";
          auditChainStatusBadge.textContent = "⚠ Chain Integrity Alert";
        }
      }

      auditTrailBody.innerHTML = "";
      data.events.forEach(ev => {
        const tr = document.createElement("tr");
        const hashDisplay = ev.event_hash ? ev.event_hash.slice(0, 10) + '...' : 'GENESIS';
        tr.innerHTML = `
          <td style="font-family:'JetBrains Mono'; font-size:0.76rem; color:#94a3b8;">${ev.timestamp}</td>
          <td><span class="badge badge-neutral">${ev.action}</span></td>
          <td style="color:#818cf8; font-weight:600;">${ev.actor}</td>
          <td style="font-family:'JetBrains Mono'; color:#fff;">${ev.affected_record}</td>
          <td style="font-size:0.78rem; color:#64748b;">${ev.previous_state || '--'}</td>
          <td style="font-size:0.78rem; color:#10b981; font-weight:600;">${ev.new_state}</td>
          <td style="font-size:0.8rem; color:#cbd5e1;">${ev.reason}</td>
          <td style="font-family:'JetBrains Mono'; font-size:0.72rem; color:#6366f1;">${hashDisplay}</td>
        `;
        auditTrailBody.appendChild(tr);
      });
    } catch (err) {
      console.error("Audit trail fetch error:", err);
    }
  }

  // Verify Hash Chain Button
  if (btnVerifyAuditChain) {
    btnVerifyAuditChain.addEventListener("click", async () => {
      try {
        const res = await fetch("/api/audit-trail/verify");
        const data = await res.json();
        alert(`Cryptographic Audit Chain Status:\n\nValid: ${data.valid}\n${data.message}\nTotal Events: ${data.total_events}\nLatest Hash: ${data.latest_hash}`);
        await loadAuditTrail();
      } catch (err) {
        alert("Verification failed: " + err.message);
      }
    });
  }

  // Open "Why?" Traceability Modal
  async function openWhy(invoiceId) {
    try {
      const res = await fetch(`/api/invoices/${invoiceId}/why`);
      if (!res.ok) throw new Error("Could not load why traceability");
      const data = await res.json();

      whyModalTitle.textContent = `Decision Traceability: ${data.invoice_id}`;
      whyModalSummary.textContent = data.summary;

      // Blocking reasons
      if (data.payment_block_reasons && data.payment_block_reasons.length > 0) {
        whyBlockingReasons.innerHTML = data.payment_block_reasons.map(r => `
          <div style="padding:8px 12px; background:rgba(244,63,94,0.12); border-left:3px solid #f43f5e; color:#fecdd3; font-size:0.84rem; margin-bottom:6px; border-radius:4px;">
            ⚠️ <strong>Blocked:</strong> ${r}
          </div>
        `).join("");
      } else {
        whyBlockingReasons.innerHTML = `
          <div style="padding:8px 12px; background:rgba(16,185,129,0.12); border-left:3px solid #10b981; color:#a7f3d0; font-size:0.84rem; border-radius:4px;">
            ✓ All mandatory payment authorization controls satisfied. Eligible for electronic disbursement.
          </div>
        `;
      }

      // Reconciliation findings
      whyReconcileFindings.innerHTML = data.reconciliation_findings.map(f => `<div>• ${f}</div>`).join("");

      // Fraud findings
      whyFraudFindings.innerHTML = data.fraud_risk_findings.length > 0
        ? data.fraud_risk_findings.map(f => `<div style="color:#fb7185;">• ${f}</div>`).join("")
        : `<div style="color:#10b981;">• No structuring or fraudulent routing patterns detected.</div>`;

      whyCashAtRisk.textContent = `Cash at Risk: ${formatUSD(data.cash_at_risk_amount)}`;
      whyActionOwner.textContent = `Action Owner: ${data.action_owner}`;

      whyModal.classList.remove("hidden");
    } catch (err) {
      alert("Error loading Why traceability: " + err.message);
    }
  }
  window.sentinelOpenWhy = openWhy;

  if (btnCloseWhyModal) {
    btnCloseWhyModal.addEventListener("click", () => {
      whyModal.classList.add("hidden");
    });
  }

  // Open Dossier Modal
  async function openDossier(invoiceId) {
    activeInvoiceId = invoiceId;
    if (paymentReleaseFeedback) paymentReleaseFeedback.classList.add("hidden");
    try {
      const res = await fetch(`/api/invoices/${invoiceId}/dossier`);
      if (!res.ok) throw new Error("Could not load dossier");
      const data = await res.json();
      
      const inv = data.invoice;
      const v = data.verdict;
      const d = data.dossier;

      modalInvoiceId.textContent = `${inv.invoice_id} — ${formatUSD(inv.amount)}`;
      modalVendorName.textContent = `${inv.vendor_name} (${inv.vendor_id}) | Due: ${inv.due_date} (${inv.payment_terms}) | Status: ${inv.payment_status}`;

      if (v) {
        modalVerdictTag.textContent = v.verdict.toUpperCase().replace('_', ' ');
        modalConfidence.textContent = `Confidence: ${(v.confidence * 100).toFixed(1)}%`;
        modalPrimaryReason.textContent = v.primary_reason;
        modalAction.textContent = `Recommended Action: ${v.recommended_action}`;
        modalNextAction.textContent = `Next Best Action: ${v.next_best_action}`;

        // Banner styling
        modalVerdictBox.className = "dossier-verdict-banner";
        if (v.verdict === "auto_approve") modalVerdictBox.style.borderColor = "var(--accent-emerald)";
        else if (v.verdict === "reject_duplicate") modalVerdictBox.style.borderColor = "var(--accent-purple)";
        else if (v.verdict === "escalate_fraud") modalVerdictBox.style.borderColor = "var(--accent-rose)";
        else if (v.verdict === "hold_for_review") modalVerdictBox.style.borderColor = "var(--accent-amber)";

        // Cited evidence list
        modalCitedEvidenceList.innerHTML = "";
        if (v.cited_evidence && v.cited_evidence.length > 0) {
          v.cited_evidence.forEach(item => {
            const row = document.createElement("div");
            row.className = "cited-fact-row";
            row.innerHTML = `
              <div class="fact-field">${item.field_path} = <strong>${JSON.stringify(item.observed_value)}</strong></div>
              <div class="fact-sig">${item.significance}</div>
            `;
            modalCitedEvidenceList.appendChild(row);
          });
        }
      }

      // Populate 3-way match & 5 pillars
      if (d) {
        pillarPO.innerHTML = `<strong>Status:</strong> ${d.po_evidence.status}<br>${d.po_evidence.details}`;
        pillarGRN.innerHTML = `<strong>3-Way Match Status:</strong> ${d.receipt_evidence.match_status}<br>${d.receipt_evidence.details}`;
        pillarBank.innerHTML = `<strong>Risk Level:</strong> ${d.bank_evidence.risk_level}<br>${d.bank_evidence.details}`;
        pillarDup.innerHTML = `<strong>Risk:</strong> ${d.duplicate_evidence.is_duplicate_risk ? 'DUPLICATE MATCH DETECTED' : 'Clean'}<br>${d.duplicate_evidence.details}`;
        pillarStructuring.innerHTML = d.structuring_evidence.in_structuring_cluster
          ? `<strong class="text-rose">STRUCTURING ATTACK DETECTED:</strong> ${d.structuring_evidence.pattern_description}`
          : (d.collusion_evidence.shared_fingerprint_detected ? `<strong class="text-rose">COLLUSION DETECTED:</strong> ${d.collusion_evidence.details}` : `No cross-batch structuring or collusion detected.`);
      }

      dossierModal.classList.remove("hidden");
    } catch (err) {
      alert("Error opening dossier: " + err.message);
    }
  }
  window.sentinelOpenDossier = openDossier;

  btnCloseModal.addEventListener("click", () => {
    dossierModal.classList.add("hidden");
    activeInvoiceId = null;
  });

  if (btnOpenWhyFromDossier) {
    btnOpenWhyFromDossier.addEventListener("click", () => {
      if (activeInvoiceId) openWhy(activeInvoiceId);
    });
  }

  // Payment Release from Dossier Handler
  if (btnReleasePaymentFromDossier) {
    btnReleasePaymentFromDossier.addEventListener("click", async () => {
      if (!activeInvoiceId) return;
      try {
        paymentReleaseFeedback.classList.remove("hidden");
        paymentReleaseFeedback.style.background = "rgba(99,102,241,0.15)";
        paymentReleaseFeedback.style.color = "#c7d2fe";
        paymentReleaseFeedback.textContent = "Evaluating security gates and payment policy controls...";

        const res = await fetch(`/api/invoices/${activeInvoiceId}/release-payment`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            authorizer_role: "FINANCE_CONTROLLER",
            authorization_notes: "Manual authorization via controller console"
          })
        });

        const data = await res.json();
        if (!res.ok) {
          const detail = data.detail || {};
          const blockingList = detail.blocking_reasons || [detail.message || "Payment release denied."];
          paymentReleaseFeedback.style.background = "rgba(244,63,94,0.18)";
          paymentReleaseFeedback.style.color = "#fecdd3";
          paymentReleaseFeedback.innerHTML = `
            <strong>🛑 Payment Release Denied by Security Boundary:</strong>
            <ul style="margin:6px 0 0 16px; padding:0;">
              ${blockingList.map(r => `<li>${r}</li>`).join("")}
            </ul>
          `;
          return;
        }

        paymentReleaseFeedback.style.background = "rgba(16,185,129,0.18)";
        paymentReleaseFeedback.style.color = "#a7f3d0";
        paymentReleaseFeedback.innerHTML = `<strong>✓ Success:</strong> ${data.message}`;

        await loadLatestBatch();
        openDossier(activeInvoiceId);
      } catch (err) {
        paymentReleaseFeedback.style.background = "rgba(244,63,94,0.18)";
        paymentReleaseFeedback.style.color = "#fecdd3";
        paymentReleaseFeedback.textContent = "Payment release error: " + err.message;
      }
    });
  }

  // Human Override
  btnSubmitOverride.addEventListener("click", async () => {
    if (!activeInvoiceId) return;
    const newVerdict = overrideVerdictSelect.value;
    const notes = overrideNotes.value.trim() || "Manual controller override";

    try {
      const res = await fetch(`/api/invoice/${activeInvoiceId}/override`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_verdict: newVerdict, reviewer_notes: notes })
      });
      if (!res.ok) throw new Error("Override failed");
      
      await loadLatestBatch();
      openDossier(activeInvoiceId);
    } catch (err) {
      alert("Error applying override: " + err.message);
    }
  });

  // Open Exception Action Modal
  function openExceptionAction(exceptionId) {
    activeExceptionId = exceptionId;
    const ex = batchData.exceptions.find(e => e.exception_id === exceptionId);
    if (!ex) return;

    modalExceptionId.textContent = `${ex.exception_id} (${ex.vendor_name})`;
    modalExceptionDetails.innerHTML = `
      <div><strong>Type:</strong> ${ex.exception_type} | <strong>Severity:</strong> ${ex.severity} | <strong>Priority:</strong> ${ex.priority_score.toFixed(1)}</div>
      <div style="margin-top:6px;"><strong>Financial Impact:</strong> ${formatUSD(ex.financial_impact)}</div>
      <div style="margin-top:6px;"><strong>Evidence:</strong> ${ex.evidence_summary}</div>
      <div style="margin-top:6px; color:#818cf8;"><strong>AI Precedent Recommendation:</strong> ${ex.recommended_action}</div>
    `;
    exceptionResolutionNotes.value = ex.recommended_action;
    if (modalGrnReference) modalGrnReference.value = "";
    if (modalReceivedQty) modalReceivedQty.value = "";
    exceptionModal.classList.remove("hidden");
  }
  window.sentinelOpenExceptionAction = openExceptionAction;

  btnCloseExceptionModal.addEventListener("click", () => {
    exceptionModal.classList.add("hidden");
    activeExceptionId = null;
  });

  btnSubmitExceptionResolution.addEventListener("click", async () => {
    if (!activeExceptionId) return;
    const action = exceptionActionSelect.value;
    const notes = exceptionResolutionNotes.value.trim() || "Controller resolution applied";
    const grnRef = modalGrnReference ? modalGrnReference.value.trim() : null;
    const recQty = modalReceivedQty && modalReceivedQty.value ? parseFloat(modalReceivedQty.value) : null;

    try {
      const res = await fetch(`/api/exceptions/${activeExceptionId}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: action,
          resolution_notes: notes,
          grn_reference: grnRef || undefined,
          received_quantity: recQty || undefined
        })
      });
      if (!res.ok) throw new Error("Resolution failed");
      exceptionModal.classList.add("hidden");
      await loadLatestBatch();
    } catch (err) {
      alert("Error resolving exception: " + err.message);
    }
  });

  // Policy Modal
  btnOpenPolicy.addEventListener("click", () => {
    if (batchData.policy) {
      policyPOTolerance.value = batchData.policy.po_tolerance_pct;
      policyApprovalThreshold.value = batchData.policy.approval_threshold;
      policyDupThreshold.value = batchData.policy.duplicate_similarity_threshold;
      policyBankCooling.value = batchData.policy.bank_cooling_days;
    }
    policyModal.classList.remove("hidden");
  });

  btnClosePolicy.addEventListener("click", () => {
    policyModal.classList.add("hidden");
  });

  btnSavePolicy.addEventListener("click", async () => {
    const newPolicy = {
      po_tolerance_pct: parseFloat(policyPOTolerance.value),
      approval_threshold: parseFloat(policyApprovalThreshold.value),
      duplicate_similarity_threshold: parseFloat(policyDupThreshold.value),
      bank_cooling_days: parseInt(policyBankCooling.value),
      grn_tolerance_pct: 0.0,
      high_risk_amount_threshold: 25000.0,
      auto_approve_clean_3way: true
    };

    try {
      const res = await fetch("/api/policy/update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newPolicy)
      });
      if (!res.ok) throw new Error("Failed to update policy");
      policyModal.classList.add("hidden");
      await loadLatestBatch();
    } catch (err) {
      alert("Policy Update Error: " + err.message);
    }
  });

  window.sentinelFilterByVendor = function(vendorName) {
    searchInput.value = vendorName;
    searchQuery = vendorName.toLowerCase();
    const invTab = document.querySelector(".tab-btn[data-tab='tab-results']");
    if (invTab) invTab.click();
    renderInvoicesTable();
  };

  // Initial load
  loadLatestBatch();
});
