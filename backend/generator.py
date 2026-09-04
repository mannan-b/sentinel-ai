import random
from datetime import datetime, timedelta
from typing import List, Tuple, Dict
from backend.models import Invoice, PurchaseOrder, VendorMaster, GroundTruthLabel

# Standard approval threshold in enterprise AP
APPROVAL_THRESHOLD = 10000.0

ESTABLISHED_VENDORS = [
    {"vendor_id": "VEND-101", "vendor_name": "CloudScale Infrastructure LLC", "avg_amount": 14500.0, "fingerprint": "BNK-US-9912-CHASE-01"},
    {"vendor_id": "VEND-102", "vendor_name": "Datasync Software Systems", "avg_amount": 4200.0, "fingerprint": "BNK-US-4819-BOFA-02"},
    {"vendor_id": "VEND-103", "vendor_name": "Global Office Supplies Co.", "avg_amount": 1850.0, "fingerprint": "BNK-US-3321-WELLS-01"},
    {"vendor_id": "VEND-104", "vendor_name": "Metro Logistics & Freight", "avg_amount": 6700.0, "fingerprint": "BNK-US-7782-CITI-04"},
    {"vendor_id": "VEND-105", "vendor_name": "CyberShield Defense Corp", "avg_amount": 18900.0, "fingerprint": "BNK-US-1190-SVB-01"},
    {"vendor_id": "VEND-106", "vendor_name": "NexGen Telecom Solutions", "avg_amount": 3100.0, "fingerprint": "BNK-US-6643-PNC-02"},
    {"vendor_id": "VEND-107", "vendor_name": "Pinnacle Facilities & Maintenance", "avg_amount": 5400.0, "fingerprint": "BNK-US-5512-USBNK-03"},
    {"vendor_id": "VEND-108", "vendor_name": "Apex Security & Guarding LLC", "avg_amount": 8500.0, "fingerprint": "BNK-US-8841-CHASE-05"},
    {"vendor_id": "VEND-109", "vendor_name": "Swift Logistics Express", "avg_amount": 2900.0, "fingerprint": "BNK-US-2234-BOFA-08"},
    {"vendor_id": "VEND-110", "vendor_name": "Evergreen Legal Advisory Group", "avg_amount": 12000.0, "fingerprint": "BNK-US-9901-WELLS-07"},
]

def generate_synthetic_batch(
    seed: int = 42,
    total_invoices: int = 75
) -> Tuple[List[Invoice], List[PurchaseOrder], List[VendorMaster], Dict[str, str]]:
    """
    Generates a deterministic synthetic dataset containing:
    - Vendor master records
    - Purchase orders
    - Invoice batch with deliberately engineered fraud, duplicate, and structuring patterns.
    """
    random.seed(seed)
    base_date = datetime(2026, 8, 1)

    vendor_masters: List[VendorMaster] = []
    vendor_dict: Dict[str, VendorMaster] = {}
    vendor_recent_bank_changes: Dict[str, int] = {} # vendor_id -> days ago bank was modified

    for v in ESTABLISHED_VENDORS:
        vm = VendorMaster(
            vendor_id=v["vendor_id"],
            vendor_name=v["vendor_name"],
            primary_bank_fingerprint=v["fingerprint"],
            established_date="2023-01-15",
            historical_invoice_count=random.randint(24, 120),
            historical_avg_amount=v["avg_amount"],
            is_trusted=True
        )
        vendor_masters.append(vm)
        vendor_dict[vm.vendor_id] = vm

    purchase_orders: List[PurchaseOrder] = []
    invoices: List[Invoice] = []
    
    # ----------------------------------------------------
    # 1. Engineered Pattern: Cross-Batch Structuring (Smurfing)
    # Vendor: Apex Security & Guarding LLC (VEND-108)
    # Obligation: $38,000 service split into 4 invoices of $9,500 each,
    # right below the $10,000 single-invoice approval threshold, submitted in a 3-day window.
    # ----------------------------------------------------
    structuring_vendor = vendor_dict["VEND-108"]
    structuring_dates = [
        base_date + timedelta(days=12),
        base_date + timedelta(days=13),
        base_date + timedelta(days=14),
        base_date + timedelta(days=14),
    ]
    for idx, s_date in enumerate(structuring_dates, start=1):
        inv_id = f"INV-STRUC-{100 + idx}"
        invoices.append(Invoice(
            invoice_id=inv_id,
            vendor_name=structuring_vendor.vendor_name,
            vendor_id=structuring_vendor.vendor_id,
            amount=9500.00,
            po_reference=None, # No PO to bypass PO control or split PO
            vendor_bank_fingerprint=structuring_vendor.primary_bank_fingerprint,
            invoice_date=s_date.strftime("%Y-%m-%d"),
            submission_date=(s_date + timedelta(days=1)).strftime("%Y-%m-%d"),
            line_items_summary=f"Supplemental security patrol installment #{idx} of facility coverage",
            ground_truth_label="fraud_risk",
            ground_truth_reason="Cross-invoice structuring: 4 invoices of $9,500 ($38k total) structured under $10,000 threshold within 3 days without PO"
        ))

    # ----------------------------------------------------
    # 2. Engineered Pattern: Bank Account Takeover / Recent Fingerprint Change
    # Vendor: CyberShield Defense Corp (VEND-105)
    # Bank account fingerprint changed 2 days prior to submission (Rogue bank change / compromised AP)
    # ----------------------------------------------------
    compromised_vendor = vendor_dict["VEND-105"]
    vendor_recent_bank_changes[compromised_vendor.vendor_id] = 2 # Changed 2 days ago
    
    po_comp = PurchaseOrder(
        po_number="PO-2026-8801",
        vendor_id=compromised_vendor.vendor_id,
        vendor_name=compromised_vendor.vendor_name,
        approved_amount=21500.00,
        description="Annual enterprise firewall & SOC monitoring subscription",
        created_date=(base_date + timedelta(days=5)).strftime("%Y-%m-%d"),
        is_active=True
    )
    purchase_orders.append(po_comp)
    
    invoices.append(Invoice(
        invoice_id="INV-CYBER-9021",
        vendor_name=compromised_vendor.vendor_name,
        vendor_id=compromised_vendor.vendor_id,
        amount=21500.00,
        po_reference=po_comp.po_number,
        vendor_bank_fingerprint="BNK-ROUTED-OFFSHORE-99X", # Changed fingerprint!
        invoice_date=(base_date + timedelta(days=16)).strftime("%Y-%m-%d"),
        submission_date=(base_date + timedelta(days=17)).strftime("%Y-%m-%d"),
        line_items_summary="SOC 24/7 managed security monitoring services",
        ground_truth_label="fraud_risk",
        ground_truth_reason="Bank fingerprint mismatch: Bank routing changed 2 days ago to unverified overseas/new routing account"
    ))

    # ----------------------------------------------------
    # 3. Engineered Pattern: First-time Unknown Vendor submitting massive un-PO'd invoice
    # Vendor: "Titanium Cybernetic Global Inc" (Brand new, 0 history, $48,750)
    # ----------------------------------------------------
    new_vendor_id = "VEND-NEW-999"
    new_vendor_name = "Titanium Cybernetic Global Inc"
    new_vm = VendorMaster(
        vendor_id=new_vendor_id,
        vendor_name=new_vendor_name,
        primary_bank_fingerprint="BNK-US-NEW-7731-WF",
        established_date="2026-08-01",
        historical_invoice_count=0, # 0 historical invoices
        historical_avg_amount=0.0,
        is_trusted=False
    )
    vendor_masters.append(new_vm)
    vendor_dict[new_vendor_id] = new_vm
    
    invoices.append(Invoice(
        invoice_id="INV-TITAN-001",
        vendor_name=new_vendor_name,
        vendor_id=new_vendor_id,
        amount=48750.00,
        po_reference=None, # Missing PO
        vendor_bank_fingerprint="BNK-US-NEW-7731-WF",
        invoice_date=(base_date + timedelta(days=18)).strftime("%Y-%m-%d"),
        submission_date=(base_date + timedelta(days=19)).strftime("%Y-%m-%d"),
        line_items_summary="Enterprise AI hardware procurement & GPU cluster consultation",
        ground_truth_label="needs_review",
        ground_truth_reason="First-time unknown vendor with large $48,750 invoice and no approved PO; requires AP manager verification"
    ))

    # ----------------------------------------------------
    # 4. Engineered Pattern: Exact Duplicates (Resubmission)
    # Vendor: CloudScale Infrastructure LLC (VEND-101)
    # ----------------------------------------------------
    po_exact = PurchaseOrder(
        po_number="PO-2026-1044",
        vendor_id="VEND-101",
        vendor_name="CloudScale Infrastructure LLC",
        approved_amount=14500.00,
        description="US-East Server hosting & egress bandwidth",
        created_date=(base_date + timedelta(days=2)).strftime("%Y-%m-%d"),
        is_active=True
    )
    purchase_orders.append(po_exact)
    
    # Original invoice
    invoices.append(Invoice(
        invoice_id="INV-CS-4401",
        vendor_name="CloudScale Infrastructure LLC",
        vendor_id="VEND-101",
        amount=14500.00,
        po_reference=po_exact.po_number,
        vendor_bank_fingerprint=vendor_dict["VEND-101"].primary_bank_fingerprint,
        invoice_date=(base_date + timedelta(days=5)).strftime("%Y-%m-%d"),
        submission_date=(base_date + timedelta(days=6)).strftime("%Y-%m-%d"),
        line_items_summary="Monthly cloud hosting compute & egress services",
        ground_truth_label="legitimate",
        ground_truth_reason="Original legitimate invoice matching PO exactly"
    ))
    
    # Exact duplicate resubmission (same invoice_id or duplicate payload)
    invoices.append(Invoice(
        invoice_id="INV-CS-4401-DUP",
        vendor_name="CloudScale Infrastructure LLC",
        vendor_id="VEND-101",
        amount=14500.00,
        po_reference=po_exact.po_number,
        vendor_bank_fingerprint=vendor_dict["VEND-101"].primary_bank_fingerprint,
        invoice_date=(base_date + timedelta(days=5)).strftime("%Y-%m-%d"),
        submission_date=(base_date + timedelta(days=9)).strftime("%Y-%m-%d"),
        line_items_summary="Monthly cloud hosting compute & egress services (Resubmitted)",
        ground_truth_label="duplicate",
        ground_truth_reason="Exact duplicate of INV-CS-4401: identical vendor, amount $14,500, and matching PO"
    ))

    # ----------------------------------------------------
    # 5. Engineered Pattern: Near Duplicates (Date shift / minor ID variation)
    # Vendor: Metro Logistics & Freight (VEND-104)
    # ----------------------------------------------------
    po_near = PurchaseOrder(
        po_number="PO-2026-3392",
        vendor_id="VEND-104",
        vendor_name="Metro Logistics & Freight",
        approved_amount=6700.00,
        description="Regional pallet distribution & expedited freight",
        created_date=(base_date + timedelta(days=4)).strftime("%Y-%m-%d"),
        is_active=True
    )
    purchase_orders.append(po_near)
    
    invoices.append(Invoice(
        invoice_id="INV-METRO-781",
        vendor_name="Metro Logistics & Freight",
        vendor_id="VEND-104",
        amount=6700.00,
        po_reference=po_near.po_number,
        vendor_bank_fingerprint=vendor_dict["VEND-104"].primary_bank_fingerprint,
        invoice_date=(base_date + timedelta(days=8)).strftime("%Y-%m-%d"),
        submission_date=(base_date + timedelta(days=9)).strftime("%Y-%m-%d"),
        line_items_summary="Midwest distribution logistics - Batch 1",
        ground_truth_label="legitimate",
        ground_truth_reason="Primary legitimate logistics billing"
    ))
    
    # Near duplicate: Same vendor, identical $6,700 amount, invoice date shifted by 2 days, different invoice ID
    invoices.append(Invoice(
        invoice_id="INV-METRO-781B",
        vendor_name="Metro Logistics & Freight",
        vendor_id="VEND-104",
        amount=6700.00,
        po_reference=po_near.po_number,
        vendor_bank_fingerprint=vendor_dict["VEND-104"].primary_bank_fingerprint,
        invoice_date=(base_date + timedelta(days=10)).strftime("%Y-%m-%d"),
        submission_date=(base_date + timedelta(days=11)).strftime("%Y-%m-%d"),
        line_items_summary="Midwest distribution logistics - Billing adjustment copy",
        ground_truth_label="duplicate",
        ground_truth_reason="Near-duplicate of INV-METRO-781: identical vendor and $6,700 amount within 2-day window"
    ))

    # ----------------------------------------------------
    # 6. Engineered Pattern: Orphan Invoices (No PO or PO tolerance mismatch)
    # Vendor: Datasync Software Systems (VEND-102) & Pinnacle (VEND-107)
    # ----------------------------------------------------
    invoices.append(Invoice(
        invoice_id="INV-DATA-ORPHAN-01",
        vendor_name="Datasync Software Systems",
        vendor_id="VEND-102",
        amount=4200.00,
        po_reference=None, # Orphan invoice, no PO referenced
        vendor_bank_fingerprint=vendor_dict["VEND-102"].primary_bank_fingerprint,
        invoice_date=(base_date + timedelta(days=7)).strftime("%Y-%m-%d"),
        submission_date=(base_date + timedelta(days=8)).strftime("%Y-%m-%d"),
        line_items_summary="Ad-hoc database tuning & query index optimization",
        ground_truth_label="needs_review",
        ground_truth_reason="Orphan invoice: established vendor submitted bill with no PO reference"
    ))

    # Invalid PO reference (PO doesn't exist)
    invoices.append(Invoice(
        invoice_id="INV-PINN-INVALID-PO",
        vendor_name="Pinnacle Facilities & Maintenance",
        vendor_id="VEND-107",
        amount=5400.00,
        po_reference="PO-NON-EXISTENT-9999", # Invalid PO
        vendor_bank_fingerprint=vendor_dict["VEND-107"].primary_bank_fingerprint,
        invoice_date=(base_date + timedelta(days=11)).strftime("%Y-%m-%d"),
        submission_date=(base_date + timedelta(days=12)).strftime("%Y-%m-%d"),
        line_items_summary="HVAC filter replacement and compressor overhaul",
        ground_truth_label="needs_review",
        ground_truth_reason="Invalid PO reference: PO-NON-EXISTENT-9999 not found in master records"
    ))

    # PO amount exceeded beyond tolerance (+35% over approved PO)
    po_exceeded = PurchaseOrder(
        po_number="PO-2026-5510",
        vendor_id="VEND-106",
        vendor_name="NexGen Telecom Solutions",
        approved_amount=3000.00,
        description="SIP trunking & VoIP channels",
        created_date=(base_date + timedelta(days=1)).strftime("%Y-%m-%d"),
        is_active=True
    )
    purchase_orders.append(po_exceeded)
    
    invoices.append(Invoice(
        invoice_id="INV-NEXGEN-OVERAGE",
        vendor_name="NexGen Telecom Solutions",
        vendor_id="VEND-106",
        amount=4050.00, # +35% over PO of $3,000
        po_reference=po_exceeded.po_number,
        vendor_bank_fingerprint=vendor_dict["VEND-106"].primary_bank_fingerprint,
        invoice_date=(base_date + timedelta(days=14)).strftime("%Y-%m-%d"),
        submission_date=(base_date + timedelta(days=15)).strftime("%Y-%m-%d"),
        line_items_summary="Telecom SIP channels plus unapproved international roaming surcharge",
        ground_truth_label="needs_review",
        ground_truth_reason="Amount exceeds approved PO by 35% ($4,050 vs $3,000 approved); requires supervisor signoff"
    ))

    # ----------------------------------------------------
    # 7. Fill remainder with legitimate, clean, conforming invoices (~70%+)
    # ----------------------------------------------------
    current_count = len(invoices)
    remaining_count = max(0, total_invoices - current_count)

    # Exclude all engineered scenario vendors from generic clean filler pool
    clean_vendor_pool = [
        v for v in ESTABLISHED_VENDORS 
        if v["vendor_id"] not in ["VEND-108", "VEND-105", "VEND-104", "VEND-102", "VEND-107", "VEND-106"]
    ]

    for i in range(remaining_count):
        v_info = random.choice(clean_vendor_pool)
        v_id = v_info["vendor_id"]
        v_name = v_info["vendor_name"]
        
        # Base amount with small standard variation (±5-15%)
        multiplier = random.uniform(0.88, 1.12)
        inv_amount = round(v_info["avg_amount"] * multiplier, 2)
        
        # Approved PO matching invoice amount (within ±0 to 2% tolerance)
        po_num = f"PO-2026-{1000 + i + 100}"
        # 85% exact match, 15% tiny 1% difference
        po_amount = inv_amount if random.random() < 0.85 else round(inv_amount * random.uniform(0.99, 1.01), 2)
        
        po_date = base_date + timedelta(days=random.randint(1, 10))
        inv_date = po_date + timedelta(days=random.randint(2, 12))
        sub_date = inv_date + timedelta(days=random.randint(1, 3))
        
        po = PurchaseOrder(
            po_number=po_num,
            vendor_id=v_id,
            vendor_name=v_name,
            approved_amount=po_amount,
            description=f"Standard monthly operating service for {v_name}",
            created_date=po_date.strftime("%Y-%m-%d"),
            is_active=True
        )
        purchase_orders.append(po)
        
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
            line_items_summary=f"Regular scheduled operational billing for {v_name}",
            ground_truth_label="legitimate",
            ground_truth_reason="Clean invoice with valid matching PO, established vendor, and matching bank fingerprint"
        ))

    # Shuffle invoices to simulate real batch arrival order while maintaining seed determinism
    random.shuffle(invoices)

    return invoices, purchase_orders, vendor_masters, vendor_recent_bank_changes
