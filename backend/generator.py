import random
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional
from backend.models import (
    Invoice, PurchaseOrder, VendorMaster, GoodsReceipt, LineItem, GroundTruthLabel
)

APPROVAL_THRESHOLD = 10000.0

ESTABLISHED_VENDORS = [
    {"vendor_id": "VEND-101", "vendor_name": "CloudScale Infrastructure LLC", "avg_amount": 14500.0, "fingerprint": "BNK-US-9912-CHASE-01", "terms": "NET30"},
    {"vendor_id": "VEND-102", "vendor_name": "Datasync Software Systems", "avg_amount": 4200.0, "fingerprint": "BNK-US-4819-BOFA-02", "terms": "NET30"},
    {"vendor_id": "VEND-103", "vendor_name": "Global Office Supplies Co.", "avg_amount": 1850.0, "fingerprint": "BNK-US-3321-WELLS-01", "terms": "NET15"},
    {"vendor_id": "VEND-104", "vendor_name": "Metro Logistics & Freight", "avg_amount": 6700.0, "fingerprint": "BNK-US-7782-CITI-04", "terms": "NET30"},
    {"vendor_id": "VEND-105", "vendor_name": "CyberShield Defense Corp", "avg_amount": 18900.0, "fingerprint": "BNK-US-1190-SVB-01", "terms": "NET30"},
    {"vendor_id": "VEND-106", "vendor_name": "NexGen Telecom Solutions", "avg_amount": 3100.0, "fingerprint": "BNK-US-6643-PNC-02", "terms": "NET15"},
    {"vendor_id": "VEND-107", "vendor_name": "Pinnacle Facilities & Maintenance", "avg_amount": 5400.0, "fingerprint": "BNK-US-5512-USBNK-03", "terms": "NET30"},
    {"vendor_id": "VEND-108", "vendor_name": "Apex Security & Guarding LLC", "avg_amount": 8500.0, "fingerprint": "BNK-US-8841-CHASE-05", "terms": "NET15"},
    {"vendor_id": "VEND-109", "vendor_name": "Swift Logistics Express", "avg_amount": 2900.0, "fingerprint": "BNK-US-2234-BOFA-08", "terms": "NET30"},
    {"vendor_id": "VEND-110", "vendor_name": "Evergreen Legal Advisory Group", "avg_amount": 12000.0, "fingerprint": "BNK-US-9901-WELLS-07", "terms": "NET60"},
]

def generate_synthetic_batch(
    seed: int = 42,
    total_invoices: int = 75
) -> Tuple[List[Invoice], List[PurchaseOrder], List[GoodsReceipt], List[VendorMaster], Dict[str, int]]:
    """
    Generates a deterministic synthetic AP finance dataset containing:
    - Vendor master records (including collusion/shared bank detection test)
    - Purchase orders with detailed line items
    - Goods Receipt Notes (GRNs) for 3-way reconciliation
    - Invoices with line items, due dates, terms, and engineered forensic scenarios.
    """
    random.seed(seed)
    base_date = datetime(2026, 8, 1)

    vendor_masters: List[VendorMaster] = []
    vendor_dict: Dict[str, VendorMaster] = {}
    vendor_recent_bank_changes: Dict[str, int] = {}

    for v in ESTABLISHED_VENDORS:
        vm = VendorMaster(
            vendor_id=v["vendor_id"],
            vendor_name=v["vendor_name"],
            primary_bank_fingerprint=v["fingerprint"],
            established_date="2023-01-15",
            historical_invoice_count=random.randint(24, 120),
            historical_avg_amount=v["avg_amount"],
            is_trusted=True,
            default_payment_terms=v["terms"]
        )
        vendor_masters.append(vm)
        vendor_dict[vm.vendor_id] = vm

    purchase_orders: List[PurchaseOrder] = []
    goods_receipts: List[GoodsReceipt] = []
    invoices: List[Invoice] = []

    # Helper to calculate due date
    def get_due_date(inv_date_str: str, terms: str) -> str:
        inv_dt = datetime.strptime(inv_date_str, "%Y-%m-%d")
        days = 30
        if terms == "NET15": days = 15
        elif terms == "NET60": days = 60
        elif terms == "IMMEDIATE": days = 0
        return (inv_dt + timedelta(days=days)).strftime("%Y-%m-%d")

    # =========================================================================
    # SCENARIO 1: Cross-Batch Structuring (Smurfing)
    # Vendor: Apex Security & Guarding LLC (VEND-108)
    # 4 split un-PO'd invoices of $9,500 each ($38,000 total) within 3 days
    # =========================================================================
    structuring_vendor = vendor_dict["VEND-108"]
    structuring_dates = [
        base_date + timedelta(days=12),
        base_date + timedelta(days=13),
        base_date + timedelta(days=14),
        base_date + timedelta(days=14),
    ]
    for idx, s_date in enumerate(structuring_dates, start=1):
        inv_id = f"INV-STRUC-{100 + idx}"
        inv_d_str = s_date.strftime("%Y-%m-%d")
        sub_d_str = (s_date + timedelta(days=1)).strftime("%Y-%m-%d")
        invoices.append(Invoice(
            invoice_id=inv_id,
            vendor_name=structuring_vendor.vendor_name,
            vendor_id=structuring_vendor.vendor_id,
            amount=9500.00,
            po_reference=None,
            vendor_bank_fingerprint=structuring_vendor.primary_bank_fingerprint,
            invoice_date=inv_d_str,
            submission_date=sub_d_str,
            due_date=get_due_date(inv_d_str, "NET15"),
            payment_terms="NET15",
            line_items_summary=f"Supplemental security patrol installment #{idx} of facility coverage",
            line_items=[
                LineItem(
                    item_id=f"ITEM-SEC-{idx}",
                    description=f"Supplemental on-site security patrol installment #{idx}",
                    quantity=95.0,
                    unit_price=100.0,
                    total_amount=9500.0
                )
            ],
            payment_status="FRAUD_HOLD",
            approval_status="PENDING",
            ground_truth_label="fraud_risk",
            ground_truth_reason="Cross-invoice structuring: 4 invoices of $9,500 ($38k total) structured under $10,000 threshold within 3 days without PO"
        ))

    # =========================================================================
    # SCENARIO 2: Bank Account Takeover / Recent Fingerprint Change (BEC)
    # Vendor: CyberShield Defense Corp (VEND-105)
    # Fingerprint changed 2 days ago to unverified overseas routing
    # =========================================================================
    comp_vendor = vendor_dict["VEND-105"]
    vendor_recent_bank_changes[comp_vendor.vendor_id] = 2

    po_comp = PurchaseOrder(
        po_number="PO-2026-8801",
        vendor_id=comp_vendor.vendor_id,
        vendor_name=comp_vendor.vendor_name,
        approved_amount=21500.00,
        description="Annual enterprise firewall & SOC monitoring subscription",
        created_date=(base_date + timedelta(days=5)).strftime("%Y-%m-%d"),
        line_items=[
            LineItem(item_id="SOC-01", description="SOC 24/7 Managed Monitoring", quantity=1.0, unit_price=21500.0, total_amount=21500.0)
        ],
        is_active=True
    )
    purchase_orders.append(po_comp)

    grn_comp = GoodsReceipt(
        grn_id="GRN-2026-8801",
        po_reference=po_comp.po_number,
        vendor_id=comp_vendor.vendor_id,
        vendor_name=comp_vendor.vendor_name,
        received_date=(base_date + timedelta(days=10)).strftime("%Y-%m-%d"),
        line_items=po_comp.line_items,
        receiving_status="FULL"
    )
    goods_receipts.append(grn_comp)

    inv_c_date = (base_date + timedelta(days=16)).strftime("%Y-%m-%d")
    invoices.append(Invoice(
        invoice_id="INV-CYBER-9021",
        vendor_name=comp_vendor.vendor_name,
        vendor_id=comp_vendor.vendor_id,
        amount=21500.00,
        po_reference=po_comp.po_number,
        vendor_bank_fingerprint="BNK-ROUTED-OFFSHORE-99X", # Changed!
        invoice_date=inv_c_date,
        submission_date=(base_date + timedelta(days=17)).strftime("%Y-%m-%d"),
        due_date=get_due_date(inv_c_date, "NET30"),
        payment_terms="NET30",
        line_items_summary="SOC 24/7 managed security monitoring services",
        line_items=po_comp.line_items,
        payment_status="FRAUD_HOLD",
        approval_status="PENDING",
        ground_truth_label="fraud_risk",
        ground_truth_reason="Bank fingerprint mismatch: Bank routing changed 2 days ago to unverified overseas/new routing account"
    ))

    # =========================================================================
    # SCENARIO 3: 3-Way Reconciliation: Quantity Overbilled (Invoice Qty > Received Qty)
    # Vendor: Global Office Supplies Co. (VEND-103)
    # PO: 100 units @ $25 = $2,500. GRN: 60 units received @ $25 = $1,500. Invoice: Billed for 100 units = $2,500.
    # =========================================================================
    po_qty_mismatch = PurchaseOrder(
        po_number="PO-2026-3011",
        vendor_id="VEND-103",
        vendor_name="Global Office Supplies Co.",
        approved_amount=2500.00,
        description="Ergonomic dual-monitor arms and desk accessories",
        created_date=(base_date + timedelta(days=3)).strftime("%Y-%m-%d"),
        line_items=[
            LineItem(item_id="DESK-ARM-01", description="Ergonomic dual-monitor arm", quantity=100.0, unit_price=25.0, total_amount=2500.0)
        ]
    )
    purchase_orders.append(po_qty_mismatch)

    grn_qty_mismatch = GoodsReceipt(
        grn_id="GRN-2026-3011",
        po_reference=po_qty_mismatch.po_number,
        vendor_id="VEND-103",
        vendor_name="Global Office Supplies Co.",
        received_date=(base_date + timedelta(days=8)).strftime("%Y-%m-%d"),
        line_items=[
            LineItem(item_id="DESK-ARM-01", description="Ergonomic dual-monitor arm", quantity=60.0, unit_price=25.0, total_amount=1500.0)
        ],
        receiving_status="PARTIAL",
        notes="Only 60 of 100 units delivered; remaining 40 backordered by supplier."
    )
    goods_receipts.append(grn_qty_mismatch)

    inv_q_date = (base_date + timedelta(days=10)).strftime("%Y-%m-%d")
    invoices.append(Invoice(
        invoice_id="INV-GOS-QTY-OVERBILL",
        vendor_name="Global Office Supplies Co.",
        vendor_id="VEND-103",
        amount=2500.00, # Invoiced for full 100 units instead of 60 received
        po_reference=po_qty_mismatch.po_number,
        vendor_bank_fingerprint=vendor_dict["VEND-103"].primary_bank_fingerprint,
        invoice_date=inv_q_date,
        submission_date=(base_date + timedelta(days=11)).strftime("%Y-%m-%d"),
        due_date=get_due_date(inv_q_date, "NET15"),
        payment_terms="NET15",
        line_items_summary="100x Ergonomic dual-monitor arms",
        line_items=[
            LineItem(item_id="DESK-ARM-01", description="Ergonomic dual-monitor arm", quantity=100.0, unit_price=25.0, total_amount=2500.0)
        ],
        payment_status="BLOCKED_BY_RECONCILIATION",
        approval_status="PENDING",
        ground_truth_label="needs_review",
        ground_truth_reason="3-Way match exception: Invoice billed 100 units ($2,500) but warehouse GRN only received 60 units ($1,500); short by 40 units ($1,000 overbilled)"
    ))

    # =========================================================================
    # SCENARIO 4: 3-Way Reconciliation: Unit Price Mismatch
    # Vendor: Datasync Software Systems (VEND-102)
    # PO: 10 licenses @ $420 = $4,200. GRN: 10 licenses received. Invoice: Billed at $520/lic = $5,200.
    # =========================================================================
    po_price_mismatch = PurchaseOrder(
        po_number="PO-2026-4202",
        vendor_id="VEND-102",
        vendor_name="Datasync Software Systems",
        approved_amount=4200.00,
        description="Database enterprise monitoring licenses",
        created_date=(base_date + timedelta(days=4)).strftime("%Y-%m-%d"),
        line_items=[
            LineItem(item_id="LIC-DB-01", description="Database Enterprise License", quantity=10.0, unit_price=420.0, total_amount=4200.0)
        ]
    )
    purchase_orders.append(po_price_mismatch)

    grn_price_mismatch = GoodsReceipt(
        grn_id="GRN-2026-4202",
        po_reference=po_price_mismatch.po_number,
        vendor_id="VEND-102",
        vendor_name="Datasync Software Systems",
        received_date=(base_date + timedelta(days=9)).strftime("%Y-%m-%d"),
        line_items=[
            LineItem(item_id="LIC-DB-01", description="Database Enterprise License", quantity=10.0, unit_price=420.0, total_amount=4200.0)
        ],
        receiving_status="FULL"
    )
    goods_receipts.append(grn_price_mismatch)

    inv_p_date = (base_date + timedelta(days=12)).strftime("%Y-%m-%d")
    invoices.append(Invoice(
        invoice_id="INV-DATA-PRICE-OVER",
        vendor_name="Datasync Software Systems",
        vendor_id="VEND-102",
        amount=5200.00, # $520/unit instead of $420 approved
        po_reference=po_price_mismatch.po_number,
        vendor_bank_fingerprint=vendor_dict["VEND-102"].primary_bank_fingerprint,
        invoice_date=inv_p_date,
        submission_date=(base_date + timedelta(days=13)).strftime("%Y-%m-%d"),
        due_date=get_due_date(inv_p_date, "NET30"),
        payment_terms="NET30",
        line_items_summary="10x Database Enterprise License @ $520 unapproved rate",
        line_items=[
            LineItem(item_id="LIC-DB-01", description="Database Enterprise License", quantity=10.0, unit_price=520.0, total_amount=5200.0)
        ],
        payment_status="BLOCKED_BY_RECONCILIATION",
        approval_status="PENDING",
        ground_truth_label="needs_review",
        ground_truth_reason="3-Way match exception: Unit price mismatch ($520.00 billed vs $420.00 PO approved rate, +$1,000 price variance)"
    ))

    # =========================================================================
    # SCENARIO 5: 3-Way Reconciliation: Missing GRN (Invoiced Before Goods Receipt)
    # Vendor: Metro Logistics & Freight (VEND-104)
    # PO exists ($6,700), but dock has not received goods (0 GRN)
    # =========================================================================
    po_missing_grn = PurchaseOrder(
        po_number="PO-2026-6701",
        vendor_id="VEND-104",
        vendor_name="Metro Logistics & Freight",
        approved_amount=6700.00,
        description="Expedited cross-country freight containers",
        created_date=(base_date + timedelta(days=6)).strftime("%Y-%m-%d"),
        line_items=[
            LineItem(item_id="FRT-CONTAINER-01", description="Cross-country container freight", quantity=2.0, unit_price=3350.0, total_amount=6700.0)
        ]
    )
    purchase_orders.append(po_missing_grn)
    # (No GRN created - missing goods receipt)

    inv_mgrn_date = (base_date + timedelta(days=10)).strftime("%Y-%m-%d")
    invoices.append(Invoice(
        invoice_id="INV-METRO-MISSING-GRN",
        vendor_name="Metro Logistics & Freight",
        vendor_id="VEND-104",
        amount=6700.00,
        po_reference=po_missing_grn.po_number,
        vendor_bank_fingerprint=vendor_dict["VEND-104"].primary_bank_fingerprint,
        invoice_date=inv_mgrn_date,
        submission_date=(base_date + timedelta(days=11)).strftime("%Y-%m-%d"),
        due_date=get_due_date(inv_mgrn_date, "NET30"),
        payment_terms="NET30",
        line_items_summary="2x Cross-country container freight (Invoiced prior to delivery)",
        line_items=po_missing_grn.line_items,
        payment_status="MISSING_DOCUMENTATION",
        approval_status="PENDING",
        ground_truth_label="needs_review",
        ground_truth_reason="3-Way match exception: Missing Goods Receipt Note (GRN); invoice billed before warehouse dock verified receiving"
    ))

    # =========================================================================
    # SCENARIO 6: 3-Way Reconciliation: Extra Line Item on Invoice Not in PO
    # Vendor: Pinnacle Facilities & Maintenance (VEND-107)
    # =========================================================================
    po_extra_line = PurchaseOrder(
        po_number="PO-2026-5401",
        vendor_id="VEND-107",
        vendor_name="Pinnacle Facilities & Maintenance",
        approved_amount=5400.00,
        description="Quarterly HVAC mechanical servicing",
        created_date=(base_date + timedelta(days=2)).strftime("%Y-%m-%d"),
        line_items=[
            LineItem(item_id="HVAC-MAINT", description="Quarterly HVAC maintenance contract", quantity=1.0, unit_price=5400.0, total_amount=5400.0)
        ]
    )
    purchase_orders.append(po_extra_line)

    grn_extra_line = GoodsReceipt(
        grn_id="GRN-2026-5401",
        po_reference=po_extra_line.po_number,
        vendor_id="VEND-107",
        vendor_name="Pinnacle Facilities & Maintenance",
        received_date=(base_date + timedelta(days=7)).strftime("%Y-%m-%d"),
        line_items=po_extra_line.line_items,
        receiving_status="FULL"
    )
    goods_receipts.append(grn_extra_line)

    inv_extra_date = (base_date + timedelta(days=12)).strftime("%Y-%m-%d")
    invoices.append(Invoice(
        invoice_id="INV-PINN-EXTRA-LINE",
        vendor_name="Pinnacle Facilities & Maintenance",
        vendor_id="VEND-107",
        amount=6600.00, # $5,400 maintenance + $1,200 unapproved surcharge
        po_reference=po_extra_line.po_number,
        vendor_bank_fingerprint=vendor_dict["VEND-107"].primary_bank_fingerprint,
        invoice_date=inv_extra_date,
        submission_date=(base_date + timedelta(days=13)).strftime("%Y-%m-%d"),
        due_date=get_due_date(inv_extra_date, "NET30"),
        payment_terms="NET30",
        line_items_summary="Quarterly HVAC maintenance plus unapproved emergency callout surcharge",
        line_items=[
            LineItem(item_id="HVAC-MAINT", description="Quarterly HVAC maintenance contract", quantity=1.0, unit_price=5400.0, total_amount=5400.0),
            LineItem(item_id="SURCHARGE-EMERGENCY", description="Unapproved emergency dispatch fee", quantity=1.0, unit_price=1200.0, total_amount=1200.0)
        ],
        payment_status="BLOCKED_BY_RECONCILIATION",
        approval_status="PENDING",
        ground_truth_label="needs_review",
        ground_truth_reason="3-Way match exception: Extra unapproved line item 'SURCHARGE-EMERGENCY' ($1,200.00) not present on approved Purchase Order"
    ))

    # =========================================================================
    # SCENARIO 7: Exact Duplicate Resubmission
    # Vendor: CloudScale Infrastructure LLC (VEND-101)
    # =========================================================================
    po_exact = PurchaseOrder(
        po_number="PO-2026-1044",
        vendor_id="VEND-101",
        vendor_name="CloudScale Infrastructure LLC",
        approved_amount=14500.00,
        description="US-East Server hosting & compute bandwidth",
        created_date=(base_date + timedelta(days=2)).strftime("%Y-%m-%d"),
        line_items=[
            LineItem(item_id="HOST-COMPUTE-01", description="US-East Server Hosting compute cluster", quantity=1.0, unit_price=14500.0, total_amount=14500.0)
        ]
    )
    purchase_orders.append(po_exact)

    grn_exact = GoodsReceipt(
        grn_id="GRN-2026-1044",
        po_reference=po_exact.po_number,
        vendor_id="VEND-101",
        vendor_name="CloudScale Infrastructure LLC",
        received_date=(base_date + timedelta(days=4)).strftime("%Y-%m-%d"),
        line_items=po_exact.line_items,
        receiving_status="FULL"
    )
    goods_receipts.append(grn_exact)

    inv_orig_date = (base_date + timedelta(days=5)).strftime("%Y-%m-%d")
    invoices.append(Invoice(
        invoice_id="INV-CS-4401",
        vendor_name="CloudScale Infrastructure LLC",
        vendor_id="VEND-101",
        amount=14500.00,
        po_reference=po_exact.po_number,
        vendor_bank_fingerprint=vendor_dict["VEND-101"].primary_bank_fingerprint,
        invoice_date=inv_orig_date,
        submission_date=(base_date + timedelta(days=6)).strftime("%Y-%m-%d"),
        due_date=get_due_date(inv_orig_date, "NET30"),
        payment_terms="NET30",
        line_items_summary="Monthly cloud hosting compute & egress services",
        line_items=po_exact.line_items,
        payment_status="READY_FOR_PAYMENT",
        approval_status="APPROVED",
        ground_truth_label="legitimate",
        ground_truth_reason="Original legitimate invoice matching PO exactly"
    ))

    invoices.append(Invoice(
        invoice_id="INV-CS-4401-DUP",
        vendor_name="CloudScale Infrastructure LLC",
        vendor_id="VEND-101",
        amount=14500.00,
        po_reference=po_exact.po_number,
        vendor_bank_fingerprint=vendor_dict["VEND-101"].primary_bank_fingerprint,
        invoice_date=inv_orig_date,
        submission_date=(base_date + timedelta(days=9)).strftime("%Y-%m-%d"), # Later sub date
        due_date=get_due_date(inv_orig_date, "NET30"),
        payment_terms="NET30",
        line_items_summary="Monthly cloud hosting compute & egress services (Resubmitted)",
        line_items=po_exact.line_items,
        payment_status="DUPLICATE_REJECTED",
        approval_status="REJECTED",
        ground_truth_label="duplicate",
        ground_truth_reason="Exact duplicate of INV-CS-4401: identical vendor, amount $14,500, and matching PO"
    ))

    # =========================================================================
    # SCENARIO 8: Near Duplicate (Shifted Date & Number Variation)
    # Vendor: Metro Logistics & Freight (VEND-104)
    # =========================================================================
    po_near = PurchaseOrder(
        po_number="PO-2026-3392",
        vendor_id="VEND-104",
        vendor_name="Metro Logistics & Freight",
        approved_amount=6700.00,
        description="Regional pallet distribution & expedited freight",
        created_date=(base_date + timedelta(days=4)).strftime("%Y-%m-%d"),
        line_items=[
            LineItem(item_id="DIST-PALLET-01", description="Regional pallet distribution logistics", quantity=1.0, unit_price=6700.0, total_amount=6700.0)
        ]
    )
    purchase_orders.append(po_near)

    grn_near = GoodsReceipt(
        grn_id="GRN-2026-3392",
        po_reference=po_near.po_number,
        vendor_id="VEND-104",
        vendor_name="Metro Logistics & Freight",
        received_date=(base_date + timedelta(days=6)).strftime("%Y-%m-%d"),
        line_items=po_near.line_items,
        receiving_status="FULL"
    )
    goods_receipts.append(grn_near)

    inv_near_date1 = (base_date + timedelta(days=8)).strftime("%Y-%m-%d")
    invoices.append(Invoice(
        invoice_id="INV-METRO-781",
        vendor_name="Metro Logistics & Freight",
        vendor_id="VEND-104",
        amount=6700.00,
        po_reference=po_near.po_number,
        vendor_bank_fingerprint=vendor_dict["VEND-104"].primary_bank_fingerprint,
        invoice_date=inv_near_date1,
        submission_date=(base_date + timedelta(days=9)).strftime("%Y-%m-%d"),
        due_date=get_due_date(inv_near_date1, "NET30"),
        payment_terms="NET30",
        line_items_summary="Midwest distribution logistics - Batch 1",
        line_items=po_near.line_items,
        payment_status="READY_FOR_PAYMENT",
        approval_status="APPROVED",
        ground_truth_label="legitimate",
        ground_truth_reason="Primary legitimate logistics billing"
    ))

    inv_near_date2 = (base_date + timedelta(days=10)).strftime("%Y-%m-%d")
    invoices.append(Invoice(
        invoice_id="INV-METRO-781B",
        vendor_name="Metro Logistics & Freight",
        vendor_id="VEND-104",
        amount=6700.00,
        po_reference=po_near.po_number,
        vendor_bank_fingerprint=vendor_dict["VEND-104"].primary_bank_fingerprint,
        invoice_date=inv_near_date2,
        submission_date=(base_date + timedelta(days=11)).strftime("%Y-%m-%d"),
        due_date=get_due_date(inv_near_date2, "NET30"),
        payment_terms="NET30",
        line_items_summary="Midwest distribution logistics - Billing adjustment copy",
        line_items=po_near.line_items,
        payment_status="DUPLICATE_REJECTED",
        approval_status="REJECTED",
        ground_truth_label="duplicate",
        ground_truth_reason="Near-duplicate of INV-METRO-781: identical vendor and $6,700 amount within 2-day window"
    ))

    # =========================================================================
    # SCENARIO 9: First-Time Unknown Vendor with Unusually Large Bill ($48,750)
    # =========================================================================
    new_vendor_id = "VEND-NEW-999"
    new_vendor_name = "Titanium Cybernetic Global Inc"
    new_vm = VendorMaster(
        vendor_id=new_vendor_id,
        vendor_name=new_vendor_name,
        primary_bank_fingerprint="BNK-US-NEW-7731-WF",
        established_date="2026-08-01",
        historical_invoice_count=0,
        historical_avg_amount=0.0,
        is_trusted=False,
        default_payment_terms="NET15"
    )
    vendor_masters.append(new_vm)
    vendor_dict[new_vendor_id] = new_vm

    inv_titan_date = (base_date + timedelta(days=18)).strftime("%Y-%m-%d")
    invoices.append(Invoice(
        invoice_id="INV-TITAN-001",
        vendor_name=new_vendor_name,
        vendor_id=new_vendor_id,
        amount=48750.00,
        po_reference=None,
        vendor_bank_fingerprint="BNK-US-NEW-7731-WF",
        invoice_date=inv_titan_date,
        submission_date=(base_date + timedelta(days=19)).strftime("%Y-%m-%d"),
        due_date=get_due_date(inv_titan_date, "NET15"),
        payment_terms="NET15",
        line_items_summary="Enterprise AI hardware procurement & GPU cluster consultation",
        line_items=[
            LineItem(item_id="GPU-CLUSTER-01", description="Enterprise GPU cluster provisioning", quantity=1.0, unit_price=48750.0, total_amount=48750.0)
        ],
        payment_status="AWAITING_REVIEW",
        approval_status="PENDING",
        ground_truth_label="needs_review",
        ground_truth_reason="First-time unknown vendor with large $48,750 invoice and no approved PO; requires AP manager verification"
    ))

    # =========================================================================
    # SCENARIO 10: Vendor Collusion / Shared Bank Fingerprint
    # Two distinct vendor master records sharing identical bank fingerprint
    # Vendor 1: Swift Logistics Express (VEND-109)
    # Vendor 2: "Apex Logistics Group" (VEND-COLLUSION-01) - sharing BNK-US-2234-BOFA-08
    # =========================================================================
    collusion_vendor_id = "VEND-COLLUSION-01"
    collusion_vendor_name = "Apex Logistics Group LLC"
    col_vm = VendorMaster(
        vendor_id=collusion_vendor_id,
        vendor_name=collusion_vendor_name,
        primary_bank_fingerprint=vendor_dict["VEND-109"].primary_bank_fingerprint, # Shared fingerprint!
        established_date="2026-06-01",
        historical_invoice_count=4,
        historical_avg_amount=3100.0,
        is_trusted=False,
        default_payment_terms="NET30"
    )
    vendor_masters.append(col_vm)
    vendor_dict[collusion_vendor_id] = col_vm

    po_col = PurchaseOrder(
        po_number="PO-2026-9912",
        vendor_id=collusion_vendor_id,
        vendor_name=collusion_vendor_name,
        approved_amount=3200.00,
        description="Overnight courier and document logistics",
        created_date=(base_date + timedelta(days=5)).strftime("%Y-%m-%d"),
        line_items=[
            LineItem(item_id="COURIER-01", description="Overnight courier batch transport", quantity=1.0, unit_price=3200.0, total_amount=3200.0)
        ]
    )
    purchase_orders.append(po_col)

    grn_col = GoodsReceipt(
        grn_id="GRN-2026-9912",
        po_reference=po_col.po_number,
        vendor_id=collusion_vendor_id,
        vendor_name=collusion_vendor_name,
        received_date=(base_date + timedelta(days=8)).strftime("%Y-%m-%d"),
        line_items=po_col.line_items,
        receiving_status="FULL"
    )
    goods_receipts.append(grn_col)

    inv_col_date = (base_date + timedelta(days=12)).strftime("%Y-%m-%d")
    invoices.append(Invoice(
        invoice_id="INV-COL-9912",
        vendor_name=collusion_vendor_name,
        vendor_id=collusion_vendor_id,
        amount=3200.00,
        po_reference=po_col.po_number,
        vendor_bank_fingerprint=col_vm.primary_bank_fingerprint,
        invoice_date=inv_col_date,
        submission_date=(base_date + timedelta(days=13)).strftime("%Y-%m-%d"),
        due_date=get_due_date(inv_col_date, "NET30"),
        payment_terms="NET30",
        line_items_summary="Overnight courier batch transport services",
        line_items=po_col.line_items,
        payment_status="FRAUD_HOLD",
        approval_status="PENDING",
        ground_truth_label="fraud_risk",
        ground_truth_reason="Vendor collusion risk: Apex Logistics Group shares identical bank routing fingerprint with Swift Logistics Express"
    ))

    # =========================================================================
    # SCENARIO 11: PO Amount Tolerance Exceeded (+35%)
    # Vendor: NexGen Telecom Solutions (VEND-106)
    # =========================================================================
    po_exceeded = PurchaseOrder(
        po_number="PO-2026-5510",
        vendor_id="VEND-106",
        vendor_name="NexGen Telecom Solutions",
        approved_amount=3000.00,
        description="SIP trunking & VoIP channels",
        created_date=(base_date + timedelta(days=1)).strftime("%Y-%m-%d"),
        line_items=[
            LineItem(item_id="VOIP-TRUNK-01", description="SIP trunking channels 30-pack", quantity=1.0, unit_price=3000.0, total_amount=3000.0)
        ]
    )
    purchase_orders.append(po_exceeded)

    grn_exceeded = GoodsReceipt(
        grn_id="GRN-2026-5510",
        po_reference=po_exceeded.po_number,
        vendor_id="VEND-106",
        vendor_name="NexGen Telecom Solutions",
        received_date=(base_date + timedelta(days=5)).strftime("%Y-%m-%d"),
        line_items=po_exceeded.line_items,
        receiving_status="FULL"
    )
    goods_receipts.append(grn_exceeded)

    inv_exc_date = (base_date + timedelta(days=14)).strftime("%Y-%m-%d")
    invoices.append(Invoice(
        invoice_id="INV-NEXGEN-OVERAGE",
        vendor_name="NexGen Telecom Solutions",
        vendor_id="VEND-106",
        amount=4050.00, # +35% over PO
        po_reference=po_exceeded.po_number,
        vendor_bank_fingerprint=vendor_dict["VEND-106"].primary_bank_fingerprint,
        invoice_date=inv_exc_date,
        submission_date=(base_date + timedelta(days=15)).strftime("%Y-%m-%d"),
        due_date=get_due_date(inv_exc_date, "NET15"),
        payment_terms="NET15",
        line_items_summary="Telecom SIP channels plus unapproved international roaming surcharge",
        line_items=[
            LineItem(item_id="VOIP-TRUNK-01", description="SIP trunking channels 30-pack", quantity=1.0, unit_price=4050.0, total_amount=4050.0)
        ],
        payment_status="AWAITING_REVIEW",
        approval_status="PENDING",
        ground_truth_label="needs_review",
        ground_truth_reason="Amount exceeds approved PO by 35% ($4,050 vs $3,000 approved); requires supervisor signoff"
    ))

    # =========================================================================
    # SCENARIO 12: Clean Legitimate Baseline with 3-Way Match (~70%+ of Batch)
    # =========================================================================
    clean_vendor_pool = [
        v for v in ESTABLISHED_VENDORS 
        if v["vendor_id"] not in ["VEND-108", "VEND-105", "VEND-104", "VEND-102", "VEND-107", "VEND-106", "VEND-103", "VEND-109"]
    ]

    current_count = len(invoices)
    remaining_count = max(0, total_invoices - current_count)

    for i in range(remaining_count):
        v_info = random.choice(clean_vendor_pool)
        v_id = v_info["vendor_id"]
        v_name = v_info["vendor_name"]
        
        # Base amount with small standard variation (±5-12%)
        multiplier = random.uniform(0.90, 1.10)
        inv_amount = round(v_info["avg_amount"] * multiplier, 2)
        qty = random.choice([1.0, 2.0, 5.0, 10.0])
        unit_p = round(inv_amount / qty, 2)
        inv_amount = round(qty * unit_p, 2) # Exact product
        
        po_num = f"PO-2026-{1000 + i + 100}"
        po_date = base_date + timedelta(days=random.randint(1, 10))
        grn_date = po_date + timedelta(days=random.randint(1, 4))
        inv_date = grn_date + timedelta(days=random.randint(1, 6))
        sub_date = inv_date + timedelta(days=random.randint(1, 2))
        
        # Payment terms
        terms = v_info["terms"]
        due_d_str = get_due_date(inv_date.strftime("%Y-%m-%d"), terms)
        
        line_items = [
            LineItem(
                item_id=f"ITEM-{v_id.split('-')[1]}-{i}",
                description=f"Standard contracted operational service unit for {v_name}",
                quantity=qty,
                unit_price=unit_p,
                total_amount=inv_amount
            )
        ]
        
        # PO
        po = PurchaseOrder(
            po_number=po_num,
            vendor_id=v_id,
            vendor_name=v_name,
            approved_amount=inv_amount,
            description=f"Standard monthly operating service for {v_name}",
            created_date=po_date.strftime("%Y-%m-%d"),
            line_items=line_items,
            payment_terms=terms,
            is_active=True
        )
        purchase_orders.append(po)

        # Matching GRN
        grn = GoodsReceipt(
            grn_id=f"GRN-2026-{1000 + i + 100}",
            po_reference=po_num,
            vendor_id=v_id,
            vendor_name=v_name,
            received_date=grn_date.strftime("%Y-%m-%d"),
            line_items=line_items,
            receiving_status="FULL"
        )
        goods_receipts.append(grn)
        
        inv_id = f"INV-{v_id.split('-')[1]}-{2000 + i}"
        invoices.append(Invoice(
            invoice_id=inv_id,
            vendor_name=v_name,
            vendor_id=v_id,
            amount=inv_amount,
            po_reference=po_num,
            vendor_bank_fingerprint=v_info["fingerprint"],
            invoice_date=inv_date.strftime("%Y-%m-%d"),
            submission_date=sub_date.strftime("%Y-%m-%d"),
            due_date=due_d_str,
            payment_terms=terms,
            line_items_summary=f"Regular scheduled operational billing for {v_name}",
            line_items=line_items,
            payment_status="READY_FOR_PAYMENT",
            approval_status="APPROVED",
            ground_truth_label="legitimate",
            ground_truth_reason="Clean invoice with valid matching PO, verified Goods Receipt (GRN), and matching bank fingerprint"
        ))

    # Deterministic shuffle to simulate realistic intake order
    random.shuffle(invoices)

    return invoices, purchase_orders, goods_receipts, vendor_masters, vendor_recent_bank_changes
