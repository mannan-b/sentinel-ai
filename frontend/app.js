// Sentinel Frontend Application Controller
document.addEventListener("DOMContentLoaded", () => {
  let batchData = {
    seed: 42,
    is_analyzed: false,
    invoices: [],
    scorecard: null,
    vendors: [],
    purchase_orders: []
  };

  let currentFilter = "ALL";
  let searchQuery = "";
  let activeInvoiceId = null;

  // DOM Elements
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabContents = document.querySelectorAll(".tab-content");
  
  const btnGenerate = document.getElementById("btnGenerate");
  const btnAnalyze = document.getElementById("btnAnalyze");
  const batchSeedInput = document.getElementById("batchSeed");
  const batchSizeSelect = document.getElementById("batchSize");

  const searchInput = document.getElementById("searchInput");
  const filterPills = document.querySelectorAll(".filter-pill");
  const invoicesTableBody = document.getElementById("invoicesTableBody");

  // KPI elements
  const kpiTotal = document.getElementById("kpiTotal");
  const kpiApproved = document.getElementById("kpiApproved");
  const kpiDuplicates = document.getElementById("kpiDuplicates");
  const kpiFraud = document.getElementById("kpiFraud");
  const kpiHold = document.getElementById("kpiHold");
  const kpiAutoResolvedPct = document.getElementById("kpiAutoResolvedPct");
  const kpiApprovedPct = document.getElementById("kpiApprovedPct");

  // Counts
  const countAll = document.getElementById("countAll");
  const countApprove = document.getElementById("countApprove");
  const countDup = document.getElementById("countDup");
  const countFraud = document.getElementById("countFraud");
  const countReview = document.getElementById("countReview");

  // Modal elements
  const dossierModal = document.getElementById("dossierModal");
  const btnCloseModal = document.getElementById("btnCloseModal");
  const modalInvoiceId = document.getElementById("modalInvoiceId");
  const modalVendorName = document.getElementById("modalVendorName");
  const modalVerdictBox = document.getElementById("modalVerdictBox");
  const modalVerdictTag = document.getElementById("modalVerdictTag");
  const modalConfidence = document.getElementById("modalConfidence");
  const modalPrimaryReason = document.getElementById("modalPrimaryReason");
  const modalAction = document.getElementById("modalAction");
  const modalCitedEvidenceList = document.getElementById("modalCitedEvidenceList");

  const pillarPO = document.getElementById("pillarPO");
  const pillarBank = document.getElementById("pillarBank");
  const pillarDup = document.getElementById("pillarDup");
  const pillarVendor = document.getElementById("pillarVendor");
  const pillarStructuring = document.getElementById("pillarStructuring");

  const overrideVerdictSelect = document.getElementById("overrideVerdictSelect");
  const overrideNotes = document.getElementById("overrideNotes");
  const btnSubmitOverride = document.getElementById("btnSubmitOverride");

  // Structuring Flagship elements
  const flagshipBanner = document.getElementById("flagshipBanner");
  const flagshipChips = document.getElementById("flagshipChips");
  const btnInspectStructuring = document.getElementById("btnInspectStructuring");
  const structuringFlowGrid = document.getElementById("structuringFlowGrid");

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
    });
  });

  // Filter pills
  filterPills.forEach(pill => {
    pill.addEventListener("click", () => {
      filterPills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      currentFilter = pill.getAttribute("data-filter");
      renderTable();
    });
  });

  // Search input
  searchInput.addEventListener("input", (e) => {
    searchQuery = e.target.value.toLowerCase().trim();
    renderTable();
  });

  // Format currency
  function formatUSD(val) {
    if (val === null || val === undefined) return "$0.00";
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(val);
  }

  // Load latest batch data
  async function loadLatestBatch() {
    try {
      const res = await fetch("/api/batch/latest");
      if (!res.ok) throw new Error("Failed to load batch data");
      batchData = await res.json();
      
      // If not yet analyzed, trigger analysis automatically for instant demo experience
      if (!batchData.is_analyzed) {
        await runAnalysis();
      } else {
        updateDashboard();
      }
    } catch (err) {
      console.error("Error loading batch:", err);
    }
  }

  // Generate synthetic batch
  btnGenerate.addEventListener("click", async () => {
    const seed = parseInt(batchSeedInput.value) || 42;
    const size = parseInt(batchSizeSelect.value) || 75;

    btnGenerate.disabled = true;
    btnGenerate.innerHTML = `Generating...`;

    try {
      const res = await fetch("/api/batch/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ seed, size })
      });
      if (!res.ok) throw new Error("Batch generation failed");
      await runAnalysis();
    } catch (err) {
      alert("Error generating batch: " + err.message);
    } finally {
      btnGenerate.disabled = false;
      btnGenerate.innerHTML = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg> Generate Batch`;
    }
  });

  // Run Sentinel Analysis
  async function runAnalysis() {
    analysisOverlay.classList.remove("hidden");
    analysisProgressBar.style.width = "20%";
    analysisStatusText.textContent = "Step 1/3: Ingesting Invoices & PO Verification...";

    await new Promise(r => setTimeout(r, 400));
    analysisProgressBar.style.width = "60%";
    analysisStatusText.textContent = "Step 2/3: Running Bank Fingerprints & Cross-Batch Structuring Scans...";

    try {
      const res = await fetch("/api/batch/analyze", { method: "POST" });
      if (!res.ok) throw new Error("Analysis failed");
      
      analysisProgressBar.style.width = "90%";
      analysisStatusText.textContent = "Step 3/3: Synthesizing Evidence & Generating Agent Verdicts...";
      await new Promise(r => setTimeout(r, 300));
      
      analysisProgressBar.style.width = "100%";
      const latestRes = await fetch("/api/batch/latest");
      batchData = await latestRes.json();
      updateDashboard();
    } catch (err) {
      alert("Error running analysis: " + err.message);
    } finally {
      setTimeout(() => {
        analysisOverlay.classList.add("hidden");
      }, 300);
    }
  }

  btnAnalyze.addEventListener("click", runAnalysis);

  // Update UI with latest data
  function updateDashboard() {
    const sc = batchData.scorecard;
    if (!sc) return;

    // KPI numbers
    kpiTotal.textContent = sc.total_invoices;
    kpiApproved.textContent = sc.auto_approved_count;
    kpiDuplicates.textContent = sc.reject_duplicate_count;
    kpiFraud.textContent = sc.escalate_fraud_count;
    kpiHold.textContent = sc.held_for_review_count;
    
    kpiAutoResolvedPct.textContent = `${sc.auto_resolved_pct}% Auto-Resolved`;
    kpiApprovedPct.textContent = `${sc.auto_approved_pct}% Clean 3-Way Match`;

    // Filter counts
    countAll.textContent = sc.total_invoices;
    countApprove.textContent = sc.auto_approved_count;
    countDup.textContent = sc.reject_duplicate_count;
    countFraud.textContent = sc.escalate_fraud_count;
    countReview.textContent = sc.held_for_review_count;

    // Metrics Lab
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

    document.getElementById("metricAutoRate").textContent = `${sc.auto_resolved_pct}%`;
    document.getElementById("metricHoldRate").textContent = `${sc.human_routing_pct}%`;
    document.getElementById("metricFPCount").textContent = sc.legitimate_false_positive_count;
    document.getElementById("metricAvgCitations").textContent = `${sc.avg_evidence_citations_per_non_approval.toFixed(1)} facts / flag`;

    // Flagship structuring
    renderFlagshipBanner(sc.structuring_flagship);
    renderStructuringFlow(sc.structuring_flagship);

    renderTable();
  }

  // Render Flagship Structuring Banner
  function renderFlagshipBanner(flagship) {
    if (!flagship || !flagship.detected) {
      flagshipBanner.style.display = "none";
      return;
    }
    flagshipBanner.style.display = "flex";
    
    flagshipChips.innerHTML = "";
    flagship.cluster_invoice_ids.forEach((id, idx) => {
      const chip = document.createElement("div");
      chip.className = "flagship-chip-item";
      chip.textContent = `${id} ($9,500)`;
      chip.style.cursor = "pointer";
      chip.addEventListener("click", () => openDossier(id));
      flagshipChips.appendChild(chip);
    });
  }

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
        <div style="font-size:0.75rem; color:#64748b;">Date: ${item.invoice.invoice_date} | No PO</div>
        <button class="btn btn-secondary" style="margin-top:10px; width:100%; font-size:0.78rem; padding:6px 10px;" onclick="window.sentinelOpenDossier('${id}')">
          View Complete Dossier
        </button>
      `;
      structuringFlowGrid.appendChild(card);
    });
  }

  btnInspectStructuring.addEventListener("click", () => {
    const structTabBtn = document.querySelector(".tab-btn[data-tab='tab-structuring']");
    if (structTabBtn) structTabBtn.click();
  });

  // Filter logic
  function matchesFilter(item) {
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

  // Render Table Rows
  function renderTable() {
    invoicesTableBody.innerHTML = "";
    
    const filtered = batchData.invoices.filter(matchesFilter);

    if (filtered.length === 0) {
      invoicesTableBody.innerHTML = `
        <tr>
          <td colspan="9" style="text-align:center; padding:32px; color:#64748b;">
            No invoices matching the current filter or search criteria.
          </td>
        </tr>
      `;
      return;
    }

    filtered.forEach(item => {
      const inv = item.invoice;
      const v = item.verdict;
      const d = item.dossier;

      const tr = document.createElement("tr");

      // Verdict badge
      let badgeHtml = `<span class="badge badge-neutral">PENDING</span>`;
      if (v) {
        if (v.verdict === "auto_approve") badgeHtml = `<span class="badge badge-approved">✓ Auto-Approve</span>`;
        else if (v.verdict === "reject_duplicate") badgeHtml = `<span class="badge badge-dup">✕ Reject (Duplicate)</span>`;
        else if (v.verdict === "escalate_fraud") badgeHtml = `<span class="badge badge-fraud">⚠ Escalate (Fraud)</span>`;
        else if (v.verdict === "hold_for_review") badgeHtml = `<span class="badge badge-hold">? Hold for Review</span>`;
      }

      // PO match badge
      let poBadge = `<span style="color:#64748b;">None</span>`;
      if (d && d.po_evidence) {
        const poStatus = d.po_evidence.status;
        if (poStatus === "EXACT_MATCH") poBadge = `<span style="color:#10b981;">✓ Exact (${inv.po_reference})</span>`;
        else if (poStatus === "WITHIN_TOLERANCE") poBadge = `<span style="color:#10b981;">✓ Tolerated (${inv.po_reference})</span>`;
        else if (poStatus === "AMOUNT_EXCEEDED") poBadge = `<span style="color:#f59e0b;">+${d.po_evidence.amount_delta_pct}% Overage</span>`;
        else if (poStatus === "INVALID_PO_REFERENCE") poBadge = `<span style="color:#f43f5e;">Invalid PO Ref</span>`;
        else if (poStatus === "NO_PO_REFERENCED") poBadge = `<span style="color:#64748b;">Missing PO</span>`;
      }

      // Bank check badge
      let bankBadge = `<span style="color:#64748b;">--</span>`;
      if (d && d.bank_evidence) {
        if (d.bank_evidence.risk_level === "NORMAL") bankBadge = `<span style="color:#10b981;">Verified</span>`;
        else if (d.bank_evidence.risk_level === "HIGH_RISK_RECENT_CHANGE") bankBadge = `<span style="color:#f43f5e; font-weight:bold;">Changed 2d ago</span>`;
        else bankBadge = `<span style="color:#f59e0b;">New Vendor</span>`;
      }

      // Cited evidence mini pills
      let citedPillsHtml = "";
      if (v && v.cited_evidence) {
        v.cited_evidence.slice(0, 2).forEach(c => {
          citedPillsHtml += `<span class="cited-tag-mini">${c.field_path.split('.').pop()}: ${c.observed_value}</span>`;
        });
      }

      tr.innerHTML = `
        <td class="inv-id-cell">${inv.invoice_id}</td>
        <td>
          <div style="font-weight:600; color:#f8fafc;">${inv.vendor_name}</div>
          <div style="font-size:0.74rem; color:#64748b;">${inv.invoice_date} • Submitted ${inv.submission_date}</div>
        </td>
        <td class="inv-amount-cell">${formatUSD(inv.amount)}</td>
        <td>${poBadge}</td>
        <td>${bankBadge}</td>
        <td>${badgeHtml}</td>
        <td>
          <span class="confidence-pill">${v ? Math.round(v.confidence * 100) + '%' : '--'}</span>
        </td>
        <td>
          <div class="evidence-preview-box">
            <div class="evidence-reason-text">${v ? v.primary_reason : 'Pending'}</div>
            <div class="cited-tags-row">${citedPillsHtml}</div>
          </div>
        </td>
        <td>
          <button class="btn btn-secondary" style="padding:4px 8px; font-size:0.75rem;" onclick="window.sentinelOpenDossier('${inv.invoice_id}')">
            Dossier
          </button>
        </td>
      `;

      invoicesTableBody.appendChild(tr);
    });
  }

  // Open Dossier Modal
  async function openDossier(invoiceId) {
    activeInvoiceId = invoiceId;
    try {
      const res = await fetch(`/api/invoices/${invoiceId}/dossier`);
      if (!res.ok) throw new Error("Could not load dossier");
      const data = await res.json();
      
      const inv = data.invoice;
      const v = data.verdict;
      const d = data.dossier;

      modalInvoiceId.textContent = inv.invoice_id;
      modalVendorName.textContent = `${inv.vendor_name} (${inv.vendor_id}) — Amount: ${formatUSD(inv.amount)}`;

      if (v) {
        modalVerdictTag.textContent = v.verdict.toUpperCase().replace('_', ' ');
        modalConfidence.textContent = `Confidence: ${(v.confidence * 100).toFixed(1)}%`;
        modalPrimaryReason.textContent = v.primary_reason;
        modalAction.textContent = `Recommended Action: ${v.recommended_action}`;

        // Color coding
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
        } else {
          modalCitedEvidenceList.innerHTML = `<div style="color:#64748b; font-size:0.82rem;">Clean 3-way match. No adverse risk indicators cited.</div>`;
        }
      }

      // Populate 5 pillars
      if (d) {
        pillarPO.innerHTML = `<strong>Status:</strong> ${d.po_evidence.status}<br>${d.po_evidence.details}`;
        pillarBank.innerHTML = `<strong>Risk Level:</strong> ${d.bank_evidence.risk_level}<br>${d.bank_evidence.details}`;
        pillarDup.innerHTML = `<strong>Risk:</strong> ${d.duplicate_evidence.is_duplicate_risk ? 'DUPLICATE MATCH DETECTED' : 'Clean'}<br>${d.duplicate_evidence.details}`;
        pillarVendor.innerHTML = `<strong>Profile:</strong> ${d.vendor_history_evidence.vendor_risk_tier}<br>${d.vendor_history_evidence.details}`;
        pillarStructuring.innerHTML = d.structuring_evidence.in_structuring_cluster
          ? `<strong class="text-rose">STRUCTURING CLUSTER DETECTED:</strong> ${d.structuring_evidence.pattern_description}`
          : `No multi-invoice structuring detected for this vendor.`;
      }

      dossierModal.classList.remove("hidden");
    } catch (err) {
      alert("Error opening dossier: " + err.message);
    }
  }

  // Expose to window for inline onclick handlers
  window.sentinelOpenDossier = openDossier;

  btnCloseModal.addEventListener("click", () => {
    dossierModal.classList.add("hidden");
    activeInvoiceId = null;
  });

  // Human Override
  btnSubmitOverride.addEventListener("click", async () => {
    if (!activeInvoiceId) return;
    const newVerdict = overrideVerdictSelect.value;
    const notes = overrideNotes.value.trim() || "Manual supervisor override";

    try {
      const res = await fetch(`/api/invoice/${activeInvoiceId}/override`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_verdict: newVerdict, reviewer_notes: notes })
      });
      if (!res.ok) throw new Error("Override failed");
      
      const latestRes = await fetch("/api/batch/latest");
      batchData = await latestRes.json();
      updateDashboard();
      openDossier(activeInvoiceId);
    } catch (err) {
      alert("Error applying override: " + err.message);
    }
  });

  // Initial load
  loadLatestBatch();
});
