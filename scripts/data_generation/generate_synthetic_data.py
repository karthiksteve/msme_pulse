"""
MSME Pulse — Synthetic Data Generator
======================================
Generates production-realistic synthetic data mimicking Indian MSME banking data.

Outputs:
  synthetic_data/msmes.json             — 10,000 MSME profiles
  synthetic_data/gst_returns.json       — ~150,000+ GSTR-1/3B records
  synthetic_data/aa_accounts.json       — ~25,000 AA account records
  synthetic_data/feature_matrix.parquet — 10,000 × 20 ML feature matrix
  synthetic_data/feature_matrix.csv     — same as above in CSV format

Usage:
  python scripts/data_generation/generate_synthetic_data.py
  python scripts/data_generation/generate_synthetic_data.py --msmes 1000 --seed 42
"""

from __future__ import annotations

import argparse
import json
import os
import random
import string
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from faker import Faker

# ─────────────────────────────────────────────────────────────────────────────
# Constants & Reference Data
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "synthetic_data"

# Indian GST state codes (2-digit prefix of GSTIN)
GST_STATE_CODES: dict[str, str] = {
    "27": "Maharashtra",
    "33": "Tamil Nadu",
    "29": "Karnataka",
    "24": "Gujarat",
    "06": "Haryana",
    "07": "Delhi",
    "32": "Kerala",
    "36": "Telangana",
    "09": "Uttar Pradesh",
    "19": "West Bengal",
    "08": "Rajasthan",
    "23": "Madhya Pradesh",
    "03": "Punjab",
    "21": "Odisha",
    "20": "Jharkhand",
}

# State weights based on MSME density (census-derived)
STATE_WEIGHTS = [0.18, 0.14, 0.12, 0.10, 0.06, 0.07, 0.05, 0.06, 0.08, 0.05,
                 0.04, 0.04, 0.04, 0.03, 0.04]

# NIC industry codes with descriptions and sector characteristics
NIC_CODES: list[dict[str, Any]] = [
    {"code": "10100", "desc": "Production, processing and preserving of meat", "sector": "food",
     "rev_base": 3e6, "rev_std": 1.5e6},
    {"code": "10200", "desc": "Processing and preserving of fish", "sector": "food",
     "rev_base": 2e6, "rev_std": 1e6},
    {"code": "10300", "desc": "Processing of fruits and vegetables", "sector": "food",
     "rev_base": 4e6, "rev_std": 2e6},
    {"code": "10400", "desc": "Vegetable and animal oils and fats", "sector": "food",
     "rev_base": 5e6, "rev_std": 2.5e6},
    {"code": "10500", "desc": "Dairy products", "sector": "food", "rev_base": 6e6, "rev_std": 3e6},
    {"code": "10600", "desc": "Grain mill products, starches and starch products", "sector": "food",
     "rev_base": 4e6, "rev_std": 2e6},
    {"code": "13100", "desc": "Spinning, weaving and finishing of textiles", "sector": "textiles",
     "rev_base": 5e6, "rev_std": 3e6},
    {"code": "13200", "desc": "Other textiles", "sector": "textiles", "rev_base": 3e6, "rev_std": 1.5e6},
    {"code": "14100", "desc": "Wearing apparel except fur apparel", "sector": "textiles",
     "rev_base": 4e6, "rev_std": 2e6},
    {"code": "16100", "desc": "Sawmilling and planing of wood", "sector": "wood",
     "rev_base": 2.5e6, "rev_std": 1e6},
    {"code": "17100", "desc": "Pulp, paper and paperboard", "sector": "paper",
     "rev_base": 4e6, "rev_std": 2e6},
    {"code": "20100", "desc": "Basic chemicals", "sector": "chemicals", "rev_base": 7e6, "rev_std": 4e6},
    {"code": "20200", "desc": "Pesticides and other agrochemicals", "sector": "chemicals",
     "rev_base": 5e6, "rev_std": 3e6},
    {"code": "22100", "desc": "Rubber products", "sector": "rubber", "rev_base": 3e6, "rev_std": 1.5e6},
    {"code": "22200", "desc": "Plastics products", "sector": "rubber", "rev_base": 4e6, "rev_std": 2e6},
    {"code": "24100", "desc": "Basic iron and steel", "sector": "metals", "rev_base": 8e6, "rev_std": 5e6},
    {"code": "25100", "desc": "Structural metal products", "sector": "metals",
     "rev_base": 3e6, "rev_std": 1.5e6},
    {"code": "26100", "desc": "Electronic components and boards", "sector": "electronics",
     "rev_base": 6e6, "rev_std": 4e6},
    {"code": "28100", "desc": "General purpose machinery", "sector": "machinery",
     "rev_base": 7e6, "rev_std": 4e6},
    {"code": "28200", "desc": "Special-purpose machinery", "sector": "machinery",
     "rev_base": 5e6, "rev_std": 3e6},
    {"code": "29100", "desc": "Motor vehicles", "sector": "auto", "rev_base": 10e6, "rev_std": 6e6},
    {"code": "29200", "desc": "Auto components and parts", "sector": "auto",
     "rev_base": 6e6, "rev_std": 3e6},
    {"code": "32900", "desc": "Manufacturing n.e.c.", "sector": "misc", "rev_base": 2e6, "rev_std": 1e6},
    {"code": "45100", "desc": "Sale of motor vehicles", "sector": "trade",
     "rev_base": 12e6, "rev_std": 8e6},
    {"code": "46100", "desc": "Wholesale on a fee or contract basis", "sector": "trade",
     "rev_base": 15e6, "rev_std": 10e6},
    {"code": "46200", "desc": "Wholesale of agricultural raw materials", "sector": "trade",
     "rev_base": 10e6, "rev_std": 7e6},
    {"code": "46900", "desc": "Other wholesale trade", "sector": "trade",
     "rev_base": 8e6, "rev_std": 5e6},
    {"code": "47100", "desc": "Retail trade in non-specialised stores", "sector": "retail",
     "rev_base": 5e6, "rev_std": 3e6},
    {"code": "47200", "desc": "Retail trade, food, beverages, tobacco", "sector": "retail",
     "rev_base": 4e6, "rev_std": 2e6},
    {"code": "47900", "desc": "Retail trade not in stores or markets", "sector": "retail",
     "rev_base": 3e6, "rev_std": 1.5e6},
    {"code": "49300", "desc": "Other land transport", "sector": "logistics",
     "rev_base": 3e6, "rev_std": 1.5e6},
    {"code": "52100", "desc": "Warehousing and storage", "sector": "logistics",
     "rev_base": 4e6, "rev_std": 2e6},
    {"code": "56100", "desc": "Restaurants and mobile food service", "sector": "hospitality",
     "rev_base": 2e6, "rev_std": 1e6},
    {"code": "62010", "desc": "Computer programming and consultancy", "sector": "it",
     "rev_base": 6e6, "rev_std": 4e6},
    {"code": "62020", "desc": "Computer facilities management", "sector": "it",
     "rev_base": 4e6, "rev_std": 3e6},
    {"code": "68100", "desc": "Real estate with own or leased property", "sector": "realestate",
     "rev_base": 8e6, "rev_std": 6e6},
    {"code": "71200", "desc": "Technical testing and analysis", "sector": "services",
     "rev_base": 3e6, "rev_std": 2e6},
    {"code": "74100", "desc": "Specialised design activities", "sector": "services",
     "rev_base": 2e6, "rev_std": 1e6},
    {"code": "77100", "desc": "Renting and leasing of motor vehicles", "sector": "services",
     "rev_base": 4e6, "rev_std": 2e6},
    {"code": "82100", "desc": "Office administrative service activities", "sector": "services",
     "rev_base": 2.5e6, "rev_std": 1.5e6},
]

# NIC code selection weights (more common sectors weighted higher)
NIC_WEIGHTS = [
    1.5, 1.0, 1.5, 1.0, 1.2, 1.5,       # food
    2.0, 1.5, 2.0,                          # textiles
    1.0, 0.8,                               # wood, paper
    1.2, 0.8, 0.8, 1.0,                    # chemicals, rubber
    1.0, 1.0, 0.8, 0.8, 0.8,              # metals, electronics, machinery
    0.5, 1.2,                               # auto
    1.5,                                    # misc
    1.0, 2.5, 2.0, 2.5,                    # trade
    3.0, 2.0, 1.5,                          # retail
    1.5, 1.0,                               # logistics
    2.0,                                    # hospitality
    1.5, 1.0,                               # IT
    0.8, 1.0, 0.8, 1.0, 0.8,              # services
]

CONSTITUTIONS = ["Proprietorship", "Partnership", "Private Limited", "LLP", "OPC"]
CONSTITUTION_WEIGHTS = [0.35, 0.20, 0.30, 0.10, 0.05]

BANKS = [
    "State Bank of India", "HDFC Bank", "ICICI Bank", "Axis Bank",
    "Kotak Mahindra Bank", "Bank of Baroda", "Punjab National Bank",
    "Union Bank of India", "Canara Bank", "IDBI Bank",
]

ACCOUNT_TYPES = ["CC", "OD", "TERM_LOAN", "BILL_DISCOUNTING"]
REPAYMENT_STATUSES = ["REGULAR", "REGULAR", "REGULAR", "REGULAR", "REGULAR",
                       "REGULAR", "REGULAR", "REGULAR", "SMA_0", "SMA_1",
                       "SMA_2", "NPA"]  # ~67% regular, ~17% SMA, ~8% NPA

# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def _rand_pan(rng: random.Random) -> str:
    """
    Generate a realistic Indian PAN number.
    Format: AAAAA9999A (5 alpha, 4 digits, 1 alpha)
    4th character indicates entity type: P=Person, C=Company, F=Firm etc.
    """
    first3 = "".join(rng.choices(string.ascii_uppercase, k=3))
    entity_char = rng.choice(["P", "C", "H", "F", "A", "B", "G", "J", "L", "T"])
    name_char = rng.choice(string.ascii_uppercase)
    digits = "".join(rng.choices(string.digits, k=4))
    check = rng.choice(string.ascii_uppercase)
    return f"{first3}{entity_char}{name_char}{digits}{check}"


def _rand_gstin(pan: str, state_code: str, rng: random.Random) -> str:
    """
    Generate a realistic GSTIN from a PAN.
    Format: 2-digit state + 10-char PAN + 3-char suffix (entity number + Z + checksum)
    """
    entity_num = rng.randint(1, 9)
    checksum = rng.choice(string.digits + string.ascii_uppercase)
    return f"{state_code}{pan}{entity_num}Z{checksum}"


def _rand_cin(rng: random.Random) -> str:
    """
    Generate a realistic CIN (Corporate Identity Number) for Pvt Ltd / OPC companies.
    Format: L/U + 5 digits + 2 alpha (state) + 4 digits (year) + 3 alpha + 6 digits
    """
    status = rng.choice(["L", "U"])
    industry = f"{rng.randint(10000, 99999)}"
    state = rng.choice(["MH", "TN", "KA", "GJ", "HR", "DL", "KL", "TS", "UP", "WB"])
    year = rng.randint(1980, 2023)
    category = "".join(rng.choices(string.ascii_uppercase, k=3))
    serial = f"{rng.randint(100000, 999999)}"
    return f"{status}{industry}{state}{year}{category}{serial}"


def _financial_year(dt: datetime) -> str:
    """Return the Indian financial year string (e.g., '2023-24') for a given date."""
    if dt.month >= 4:
        return f"{dt.year}-{str(dt.year + 1)[-2:]}"
    return f"{dt.year - 1}-{str(dt.year)[-2:]}"


def _tax_period(dt: datetime) -> str:
    """Return tax period string in 'YYYY-MM' format."""
    return dt.strftime("%Y-%m")


def _generate_business_name(faker: Faker, constitution: str, sector: str) -> tuple[str, str]:
    """Generate a realistic Indian business legal and trade name."""
    suffixes = {
        "Proprietorship": ["Enterprises", "Trading Co", "& Sons", "Traders"],
        "Partnership": ["& Associates", "Partners", "& Co", "Group"],
        "Private Limited": ["Private Limited", "Pvt Ltd"],
        "LLP": ["LLP", "& Partners LLP"],
        "OPC": ["OPC Private Limited"],
    }
    sector_words = {
        "food": ["Foods", "Agro", "Dairy", "Grains", "Spices"],
        "textiles": ["Textiles", "Fabrics", "Garments", "Weaves"],
        "chemicals": ["Chemicals", "Polymers", "Pharma", "Labs"],
        "metals": ["Steel", "Metals", "Alloys", "Forge"],
        "electronics": ["Electronics", "Tech", "Systems", "Circuits"],
        "machinery": ["Engineering", "Machines", "Industries"],
        "auto": ["Auto", "Motors", "Automotive", "Wheels"],
        "trade": ["Trading", "Commerce", "Traders"],
        "retail": ["Retail", "Stores", "Mart", "Shop"],
        "it": ["Solutions", "Tech", "Digital", "InfoSystems"],
        "services": ["Services", "Consultants", "Solutions"],
        "logistics": ["Logistics", "Cargo", "Transport"],
        "hospitality": ["Foods", "Restaurants", "Catering"],
        "misc": ["Industries", "Works", "Fabricators"],
        "wood": ["Timber", "Wood", "Woodworks"],
        "paper": ["Paper", "Print", "Packaging"],
        "rubber": ["Plastics", "Polymers", "Rubberworks"],
        "realestate": ["Properties", "Realty", "Builders", "Developers"],
    }
    surname = faker.last_name()
    sector_word = random.choice(sector_words.get(sector, ["Industries"]))
    suffix = random.choice(suffixes.get(constitution, ["Enterprises"]))
    legal_name = f"{surname} {sector_word} {suffix}"
    trade_name = f"{surname} {sector_word}" if random.random() > 0.4 else legal_name
    return legal_name, trade_name


# ─────────────────────────────────────────────────────────────────────────────
# MSME Generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_msmes(n: int, rng: random.Random, faker: Faker) -> list[dict[str, Any]]:
    """
    Generate n realistic MSME profiles.
    Returns list of dicts matching the MSME SQLAlchemy model fields.
    """
    msmes = []
    used_pan: set[str] = set()
    used_gstin: set[str] = set()

    state_codes = list(GST_STATE_CODES.keys())
    state_weights_norm = [w / sum(STATE_WEIGHTS) for w in STATE_WEIGHTS]

    nic_weights_norm = [w / sum(NIC_WEIGHTS) for w in NIC_WEIGHTS]

    for _ in range(n):
        # Pick state
        state_code = rng.choices(state_codes, weights=state_weights_norm, k=1)[0]
        state_name = GST_STATE_CODES[state_code]

        # Generate unique PAN
        while True:
            pan = _rand_pan(rng)
            if pan not in used_pan:
                used_pan.add(pan)
                break

        # Generate unique GSTIN
        while True:
            gstin = _rand_gstin(pan, state_code, rng)
            if gstin not in used_gstin:
                used_gstin.add(gstin)
                break

        # Pick NIC code
        nic = rng.choices(NIC_CODES, weights=nic_weights_norm, k=1)[0]

        # Constitution
        constitution = rng.choices(CONSTITUTIONS, weights=CONSTITUTION_WEIGHTS, k=1)[0]

        # CIN only for companies
        cin = _rand_cin(rng) if constitution in ("Private Limited", "LLP", "OPC") else None

        # Incorporation date: 1 to 25 years ago, weighted towards 3-10 years
        years_ago = max(1, int(np.random.exponential(scale=6)) + 1)
        years_ago = min(years_ago, 25)
        incorporation_date = datetime.utcnow() - timedelta(days=years_ago * 365 + rng.randint(0, 365))

        # GST registration: within 1 year of incorporation, mostly same year
        gst_offset_days = rng.randint(0, min(365, (datetime.utcnow() - incorporation_date).days))
        gst_registration_date = incorporation_date + timedelta(days=gst_offset_days)

        legal_name, trade_name = _generate_business_name(faker, constitution, nic["sector"])

        # Status distribution: 88% ACTIVE, 5% INACTIVE, 4% NPA, 3% CLOSED
        status = rng.choices(
            ["active", "inactive", "npa", "closed"],
            weights=[0.88, 0.05, 0.04, 0.03], k=1
        )[0]

        # Employee count: exponential distribution, 1-500
        employees = max(1, int(np.random.exponential(scale=15)))
        employees = min(employees, 500)

        # Generate alternate data details (EPFO, cash flow, delay days)
        if status == "active":
            pf_compliance = round(rng.uniform(82.0, 100.0), 1)
            gstr_delay = rng.choice([0, 0, 0, 1, 2, 3, 5, 8])
            burn_ratio = rng.uniform(0.70, 0.88)
        else:
            pf_compliance = round(rng.uniform(35.0, 80.0), 1)
            gstr_delay = rng.randint(6, 45)
            burn_ratio = rng.uniform(0.88, 1.05)

        avg_inflow = round((nic["rev_base"] / 12) * rng.uniform(0.85, 1.25), 2)
        avg_outflow = round(avg_inflow * burn_ratio, 2)
        disposable_inc = round(avg_inflow - avg_outflow, 2)

        if disposable_inc > 0.20 * avg_inflow:
            behavior_tag = "Disciplined Spender"
        elif avg_outflow > 0.90 * avg_inflow:
            behavior_tag = "High Cash Burn"
        else:
            behavior_tag = "Moderate Spender"

        msme_id = str(uuid.uuid4())
        city = faker.city()

        msmes.append({
            "id": msme_id,
            "gstin": gstin,
            "pan": pan,
            "cin": cin,
            "legal_name": legal_name,
            "trade_name": trade_name,
            "address_line1": faker.street_address(),
            "address_line2": f"Near {faker.street_name()}",
            "city": city,
            "state": state_name,
            "pincode": f"{rng.randint(100000, 999999)}",
            "nic_code": nic["code"],
            "nic_description": nic["desc"],
            "incorporation_date": incorporation_date.isoformat(),
            "constitution": constitution,
            "status": status,
            "gst_registration_date": gst_registration_date.isoformat(),
            "epfo_active_employees": employees,
            "pf_compliance_score": pf_compliance,
            "avg_monthly_inflow": avg_inflow,
            "avg_monthly_outflow": avg_outflow,
            "disposable_income": disposable_inc,
            "gstr_3b_delay_days": gstr_delay,
            "behavioral_tag": behavior_tag,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            # Internal metadata for data generation (not in DB schema)
            "_state_code": state_code,
            "_sector": nic["sector"],
            "_rev_base": nic["rev_base"],
            "_rev_std": nic["rev_std"],
            "_years_old": years_ago,
            "_employee_count": employees,
        })

    print(f"  [OK] Generated {len(msmes)} MSME profiles")
    return msmes


# ─────────────────────────────────────────────────────────────────────────────
# GST Return Generator
# ─────────────────────────────────────────────────────────────────────────────

def _simulate_revenue_trend(msme: dict, num_months: int, rng: random.Random) -> list[float]:
    """
    Simulate monthly revenue series with realistic patterns:
    - Seasonal variation (higher in Q4: Jan-Mar for Indian FY)
    - Growth trend (positive for healthy, declining for stressed)
    - Random noise
    """
    base_rev = msme["_rev_base"] / 12  # monthly base
    std = msme["_rev_std"] / 12

    # Growth trend: mostly positive, some declining
    trend = rng.choices(
        [0.01, 0.02, 0.005, -0.01, -0.02],
        weights=[0.30, 0.25, 0.25, 0.12, 0.08], k=1
    )[0]

    revenues = []
    current = base_rev * rng.uniform(0.7, 1.3)
    for month_idx in range(num_months):
        # Apply seasonal multiplier (Indian FY Q4 = Jan-Mar = peak)
        # Using a sine wave: peak at month 12 (March) of Indian FY
        seasonal = 1.0 + 0.15 * np.sin(2 * np.pi * (month_idx % 12) / 12)
        noise = rng.normalvariate(0, std * 0.3)
        current = max(0, current * (1 + trend) + noise * seasonal)
        revenues.append(max(0, current * seasonal))

    return revenues


def generate_gst_returns(msmes: list[dict], rng: random.Random) -> list[dict[str, Any]]:
    """
    Generate GSTR-1 and GSTR-3B records for 12-24 months per MSME.
    Returns list of dicts matching GSTReturn model fields.
    """
    gst_records = []
    now = datetime.utcnow()

    for msme in msmes:
        msme_id = msme["id"]
        num_months = rng.randint(12, 24)

        # Generate revenue series for this MSME
        revenues = _simulate_revenue_trend(msme, num_months, rng)

        # Revenue mix: B2B vs B2C vs Export (sector-dependent)
        sector = msme["_sector"]
        if sector in ("trade", "retail"):
            b2b_ratio = rng.uniform(0.30, 0.60)
            export_ratio = rng.uniform(0.00, 0.05)
        elif sector in ("it", "services"):
            b2b_ratio = rng.uniform(0.60, 0.90)
            export_ratio = rng.uniform(0.05, 0.30)
        elif sector in ("textiles", "chemicals", "machinery"):
            b2b_ratio = rng.uniform(0.50, 0.80)
            export_ratio = rng.uniform(0.10, 0.40)
        else:
            b2b_ratio = rng.uniform(0.40, 0.70)
            export_ratio = rng.uniform(0.00, 0.15)

        # GST rate (sector-dependent): 5, 12, 18, or 28%
        gst_rate_map = {
            "food": 0.05, "textiles": 0.12, "chemicals": 0.18,
            "metals": 0.18, "electronics": 0.18, "machinery": 0.18,
            "auto": 0.28, "trade": 0.12, "retail": 0.12, "it": 0.18,
            "services": 0.18, "logistics": 0.05, "hospitality": 0.05,
            "misc": 0.18, "wood": 0.18, "paper": 0.12, "rubber": 0.18,
            "realestate": 0.12,
        }
        gst_rate = gst_rate_map.get(sector, 0.18)

        # ITC ratio: typically 60-90% of GST liability
        itc_ratio = rng.uniform(0.60, 0.90)

        # Filing compliance: most file on time, some late
        compliance_rate = rng.uniform(0.75, 1.00)

        for month_idx in range(num_months):
            period_date = now - timedelta(days=(num_months - month_idx) * 30)
            financial_year = _financial_year(period_date)
            tax_period = _tax_period(period_date)

            total_rev = revenues[month_idx]
            b2b_rev = total_rev * b2b_ratio
            b2c_rev = total_rev * (1 - b2b_ratio - export_ratio) * rng.uniform(0.9, 1.1)
            export_rev = total_rev * export_ratio * rng.uniform(0.8, 1.2)
            b2c_rev = max(0, b2c_rev)
            export_rev = max(0, export_rev)

            outward_supplies = total_rev
            inward_supplies = total_rev * rng.uniform(0.60, 0.85)  # cost of inputs

            igst = total_rev * gst_rate * rng.uniform(0.20, 0.40)
            cgst = total_rev * gst_rate * 0.5 * rng.uniform(0.30, 0.50)
            sgst = cgst * rng.uniform(0.95, 1.05)
            cess = 0 if sector not in ("auto", "hospitality") else total_rev * 0.01

            gst_liability = igst + cgst + sgst + cess
            itc_claimed = gst_liability * itc_ratio
            itc_reversed = itc_claimed * rng.uniform(0.0, 0.05)  # small reversals
            itc_available = itc_claimed - itc_reversed
            net_tax_payable = max(0, gst_liability - itc_available)

            # Tax paid: some late or partial payments
            if rng.random() < 0.05:  # 5% chance of non-payment
                tax_paid = net_tax_payable * rng.uniform(0.0, 0.5)
            else:
                tax_paid = net_tax_payable

            # Filing status
            is_filed = rng.random() < compliance_rate
            filing_status = "FILED" if is_filed else ("PENDING" if rng.random() > 0.5 else "REVISED")

            if is_filed:
                # Filing date: mostly on time (due dates: 20th for 3B, 11th for 1)
                due_day = 11  # GSTR-1 due
                due_date = period_date.replace(day=1) + timedelta(days=40)  # next month ~10th
                late_days = rng.choices(
                    [0, rng.randint(1, 5), rng.randint(6, 30), rng.randint(31, 90)],
                    weights=[0.70, 0.15, 0.10, 0.05], k=1
                )[0]
                filing_date = due_date + timedelta(days=late_days)
                filing_date = min(filing_date, now)
            else:
                filing_date = None

            # B2B invoice details (simplified structured data)
            num_b2b_invoices = rng.randint(3, 25)
            b2b_invoices = {
                "total_invoices": num_b2b_invoices,
                "taxable_value": b2b_rev,
                "tax_amount": b2b_rev * gst_rate,
            }

            # B2C invoices
            b2c_invoices = {
                "taxable_value": b2c_rev,
                "tax_amount": b2c_rev * gst_rate,
            }

            # Export invoices
            export_invoices = {
                "taxable_value": export_rev,
                "tax_amount": 0,  # exports are zero-rated
            } if export_rev > 0 else {}

            # HSN summary (top 3 HSN codes for the sector)
            hsn_codes = {"84": 0.6, "85": 0.3, "73": 0.1} if sector == "machinery" \
                else {"61": 0.5, "62": 0.3, "63": 0.2} if sector == "textiles" \
                else {"19": 0.7, "21": 0.2, "04": 0.1} if sector == "food" \
                else {"99": 1.0}

            hsn_summary = {
                hsn: {
                    "taxable_value": total_rev * frac,
                    "tax_amount": total_rev * frac * gst_rate,
                }
                for hsn, frac in hsn_codes.items()
            }

            # Generate records for both GSTR-1 and GSTR-3B
            for return_type in ["GSTR-1", "GSTR-3B"]:
                record = {
                    "id": str(uuid.uuid4()),
                    "msme_id": msme_id,
                    "return_type": return_type,
                    "financial_year": financial_year,
                    "tax_period": tax_period,
                    "b2b_invoices": b2b_invoices if return_type == "GSTR-1" else {},
                    "b2c_invoices": b2c_invoices if return_type == "GSTR-1" else {},
                    "export_invoices": export_invoices if return_type == "GSTR-1" else {},
                    "credit_debit_notes": {},
                    "hsn_summary": hsn_summary if return_type == "GSTR-1" else {},
                    "doc_issued": {},
                    "outward_supplies": outward_supplies,
                    "inward_supplies": inward_supplies,
                    "taxable_value": outward_supplies,
                    "igst": igst,
                    "cgst": cgst,
                    "sgst": sgst,
                    "cess": cess,
                    "itc_claimed": itc_claimed,
                    "itc_reversed": itc_reversed,
                    "net_tax_payable": net_tax_payable,
                    "tax_paid": tax_paid,
                    "total_revenue": outward_supplies + inward_supplies,
                    "b2b_revenue": b2b_rev,
                    "b2c_revenue": b2c_rev,
                    "export_revenue": export_rev,
                    "gst_liability": gst_liability,
                    "itc_available": itc_available,
                    "filing_status": filing_status,
                    "filing_date": filing_date.isoformat() if filing_date else None,
                    "created_at": datetime.utcnow().isoformat(),
                }
                gst_records.append(record)

    print(f"  [OK] Generated {len(gst_records)} GST return records")
    return gst_records


# ─────────────────────────────────────────────────────────────────────────────
# AA Account Generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_aa_accounts(msmes: list[dict], rng: random.Random) -> list[dict[str, Any]]:
    """
    Generate Account Aggregator bank account records for MSMEs.
    80% of MSMEs have at least 1 account; up to 4 accounts each.
    Repayment status distribution: ~70% REGULAR, ~17% SMA, ~8% NPA.
    """
    aa_records = []
    now = datetime.utcnow()

    for msme in msmes:
        # 80% of MSMEs have AA accounts
        if rng.random() > 0.80:
            continue

        msme_id = msme["id"]
        num_accounts = rng.choices([1, 2, 3, 4], weights=[0.40, 0.35, 0.18, 0.07], k=1)[0]

        # Overall credit health of this MSME (affects repayment status)
        is_stressed = msme["status"] in ("npa", "inactive")
        is_growing = rng.random() > 0.40

        for acc_idx in range(num_accounts):
            account_type = rng.choice(ACCOUNT_TYPES)
            bank = rng.choice(BANKS)

            # Sanctioned limit based on MSME size
            rev_monthly = msme["_rev_base"] / 12
            if account_type == "CC":
                sanctioned = rev_monthly * rng.uniform(0.5, 2.0)
            elif account_type == "OD":
                sanctioned = rev_monthly * rng.uniform(0.3, 1.5)
            elif account_type == "TERM_LOAN":
                sanctioned = msme["_rev_base"] * rng.uniform(0.5, 3.0)
            else:  # BILL_DISCOUNTING
                sanctioned = rev_monthly * rng.uniform(0.8, 2.5)

            sanctioned = max(100000, sanctioned)  # minimum 1 lakh

            # Outstanding and utilization
            if is_stressed:
                utilization = rng.uniform(0.70, 1.10)  # over-utilized
            elif is_growing:
                utilization = rng.uniform(0.40, 0.80)
            else:
                utilization = rng.uniform(0.20, 0.65)

            outstanding = sanctioned * min(utilization, 1.05)
            drawing_power = sanctioned * rng.uniform(0.85, 1.0)

            # Interest rate (base + spread)
            base_rate = rng.uniform(6.5, 8.5)
            spread = rng.uniform(1.5, 5.0)
            interest_rate = round(base_rate + spread, 2)

            # Repayment status
            if is_stressed:
                status = rng.choices(
                    ["REGULAR", "SMA_0", "SMA_1", "SMA_2", "NPA"],
                    weights=[0.20, 0.15, 0.20, 0.20, 0.25], k=1
                )[0]
            else:
                status = rng.choices(
                    ["REGULAR", "SMA_0", "SMA_1", "SMA_2", "NPA"],
                    weights=[0.82, 0.07, 0.05, 0.03, 0.03], k=1
                )[0]

            # Days past due
            dpd_map = {
                "REGULAR": 0,
                "SMA_0": rng.randint(1, 30),
                "SMA_1": rng.randint(31, 60),
                "SMA_2": rng.randint(61, 90),
                "NPA": rng.randint(91, 365),
            }
            days_past_due = dpd_map[status]

            # Overdue amount
            if status == "REGULAR":
                overdue = 0.0
            else:
                overdue = outstanding * rng.uniform(0.05, 0.40)

            # Account timeline
            years_open = rng.randint(1, min(10, msme["_years_old"]))
            account_open_date = now - timedelta(days=years_open * 365 + rng.randint(0, 365))
            last_review_date = now - timedelta(days=rng.randint(30, 365))
            maturity_date = (now + timedelta(days=rng.randint(90, 1800))
                             if account_type == "TERM_LOAN" else None)

            # Consent metadata (AA framework)
            consent_id = f"CONSENT-{uuid.uuid4().hex[:16].upper()}"
            consent_start = now - timedelta(days=rng.randint(1, 180))
            consent_expiry = consent_start + timedelta(days=365)
            consent_status = "ACTIVE" if consent_expiry > now else "EXPIRED"

            # Masked account number
            masked_acct = f"XXXXXXXX{rng.randint(1000, 9999)}"

            aa_records.append({
                "id": str(uuid.uuid4()),
                "msme_id": msme_id,
                "fi_type": "BANK",
                "fi_name": bank,
                "account_type": account_type,
                "account_number_masked": masked_acct,
                "sanctioned_limit": round(sanctioned, 2),
                "outstanding_amount": round(outstanding, 2),
                "drawing_power": round(drawing_power, 2),
                "interest_rate": interest_rate,
                "repayment_status": status,
                "days_past_due": days_past_due,
                "overdue_amount": round(overdue, 2),
                "account_open_date": account_open_date.isoformat(),
                "last_review_date": last_review_date.isoformat(),
                "maturity_date": maturity_date.isoformat() if maturity_date else None,
                "consent_id": consent_id,
                "consent_status": consent_status,
                "consent_start": consent_start.isoformat(),
                "consent_expiry": consent_expiry.isoformat(),
                "data_as_of": (now - timedelta(hours=rng.randint(1, 48))).isoformat(),
                "fetched_at": now.isoformat(),
            })

    print(f"  [OK] Generated {len(aa_records)} AA account records for {sum(1 for m in msmes if any(True for _ in [])):.0f}+ MSMEs")
    return aa_records


# ─────────────────────────────────────────────────────────────────────────────
# Feature Matrix Builder
# ─────────────────────────────────────────────────────────────────────────────

def build_feature_matrix(
    msmes: list[dict],
    gst_records: list[dict],
    aa_records: list[dict],
) -> pd.DataFrame:
    """
    Build the 20-feature ML training matrix exactly matching the format
    expected by ml_service._prepare_features().

    Features (in order):
      0:  incorporation_age              — years since incorporation (float)
      1:  is_private_limited             — 1.0 if Private Limited, else 0.0
      2:  employee_count                 — approximate headcount
      3:  total_revenue_norm             — latest GST total_revenue / 1e7
      4:  gst_liability_norm             — latest GST gst_liability / 1e6
      5:  itc_available_norm             — latest GST itc_available / 1e6
      6:  b2b_revenue_ratio              — b2b_revenue / total_revenue
      7:  export_revenue_ratio           — export_revenue / total_revenue
      8:  revenue_mean_norm              — mean(12m revenues) / 1e7
      9:  revenue_std_norm               — std(12m revenues) / 1e7
     10:  revenue_growth                 — (last - first) / first for available months
     11:  total_outstanding_norm         — sum(outstanding) / 1e7
     12:  total_sanctioned_norm          — sum(sanctioned) / 1e7
     13:  utilization_ratio              — outstanding / sanctioned
     14:  overdue_ratio                  — overdue / outstanding
     15:  npa_count                      — count of NPA accounts
     16:  sma_count                      — count of SMA accounts
     17:  cc_accounts                    — count of CC accounts
     18:  od_accounts                    — count of OD accounts
     19:  term_loan_accounts             — count of TERM_LOAN accounts

    Label columns (for training, not used in inference):
     need_working_capital
     need_machinery_capex
     need_business_expansion
     need_inventory_funding
     need_trade_finance
     need_digital_transformation
     credit_risk_label              — 1 if NPA/SMA_2, else 0
    """
    # Index GST and AA records by msme_id
    gst_by_msme: dict[str, list[dict]] = {}
    for g in gst_records:
        if g["return_type"] == "GSTR-3B":  # Use 3B for financial features
            gst_by_msme.setdefault(g["msme_id"], []).append(g)

    aa_by_msme: dict[str, list[dict]] = {}
    for a in aa_records:
        aa_by_msme.setdefault(a["msme_id"], []).append(a)

    rows = []
    for msme in msmes:
        mid = msme["id"]
        gst_list = sorted(gst_by_msme.get(mid, []), key=lambda x: x["tax_period"], reverse=True)
        aa_list = aa_by_msme.get(mid, [])

        # ── MSME profile features ──────────────────────────────────────────
        incorporation_age = msme["_years_old"]
        is_pvt_ltd = 1.0 if msme["constitution"] == "Private Limited" else 0.0
        employee_count = float(msme["_employee_count"])
        pf_compliance = float(msme.get("pf_compliance_score", 0.0))
        gstr_delay = float(msme.get("gstr_3b_delay_days", 0))
        disposable_inc_norm = float(msme.get("disposable_income", 0.0)) / 1e6

        # ── GST features ──────────────────────────────────────────────────
        if gst_list:
            latest = gst_list[0]
            total_revenue = float(latest.get("total_revenue", 0))
            gst_liability = float(latest.get("gst_liability", 0))
            itc_available = float(latest.get("itc_available", 0))
            b2b_rev = float(latest.get("b2b_revenue", 0))
            export_rev = float(latest.get("export_revenue", 0))

            b2b_ratio = b2b_rev / max(total_revenue, 1)
            export_ratio = export_rev / max(total_revenue, 1)

            revenues = [float(g.get("total_revenue", 0)) for g in gst_list[:12]]
            rev_mean = np.mean(revenues) / 1e7 if revenues else 0
            rev_std = np.std(revenues) / 1e7 if len(revenues) > 1 else 0
            rev_growth = ((revenues[0] - revenues[-1]) / max(revenues[-1], 1)
                          if len(revenues) > 1 else 0)
        else:
            total_revenue = gst_liability = itc_available = 0
            b2b_ratio = export_ratio = rev_mean = rev_std = rev_growth = 0

        # ── AA features ───────────────────────────────────────────────────
        if aa_list:
            total_outstanding = sum(float(a["outstanding_amount"]) for a in aa_list)
            total_sanctioned = sum(float(a["sanctioned_limit"]) for a in aa_list)
            total_overdue = sum(float(a["overdue_amount"]) for a in aa_list)
            npa_count = float(sum(1 for a in aa_list if a["repayment_status"] == "NPA"))
            sma_count = float(sum(1 for a in aa_list
                                   if a["repayment_status"].startswith("SMA")))
            cc_count = float(sum(1 for a in aa_list if a["account_type"] == "CC"))
            od_count = float(sum(1 for a in aa_list if a["account_type"] == "OD"))
            tl_count = float(sum(1 for a in aa_list if a["account_type"] == "TERM_LOAN"))

            utilization_ratio = total_outstanding / max(total_sanctioned, 1)
            overdue_ratio = total_overdue / max(total_outstanding, 1)
        else:
            total_outstanding = total_sanctioned = total_overdue = 0
            npa_count = sma_count = cc_count = od_count = tl_count = 0
            utilization_ratio = overdue_ratio = 0.0

        # ── Labels (multi-label need categories) ──────────────────────────
        # Derive labels from feature heuristics (realistic business rules)
        sector = msme["_sector"]
        rev = total_revenue if total_revenue > 0 else msme["_rev_base"] / 12

        # Working capital need: high utilization CC/OD, declining revenue
        need_wc = float(
            (utilization_ratio > 0.75 and cc_count + od_count > 0) or
            (rev_growth < -0.10) or
            (b2b_ratio > 0.6 and overdue_ratio > 0.05)
        )

        # Machinery/Capex: manufacturing sectors with growing revenue but low CC
        need_capex = float(
            (sector in ("machinery", "metals", "electronics", "auto", "chemicals") and
             incorporation_age >= 3 and rev > msme["_rev_base"] * 0.08) or
            (export_ratio > 0.30)
        )

        # Business expansion: young company, rapidly growing
        need_expansion = float(
            (rev_growth > 0.20 and incorporation_age < 5) or
            (export_ratio > 0.15 and is_pvt_ltd == 1.0)
        )

        # Inventory funding: trade/retail with high B2C, seasonal businesses
        need_inventory = float(
            (sector in ("trade", "retail", "food") and b2b_ratio < 0.50) or
            (rev_std / max(rev_mean, 0.001) > 0.30)  # high revenue volatility
        )

        # Trade finance: exporters, high B2B
        need_trade = float(
            (export_ratio > 0.20) or
            (b2b_ratio > 0.70 and rev > msme["_rev_base"] * 0.15)
        )

        # Digital transformation: IT sector or young companies
        need_digital = float(
            (sector == "it") or
            (incorporation_age < 3 and is_pvt_ltd == 1.0)
        )

        # Credit risk label: 1 if NPA or SMA_2 exists
        credit_risk = float(
            npa_count > 0 or
            any(a["repayment_status"] == "SMA_2" for a in aa_list)
        )

        rows.append({
            # Feature columns
            "msme_id": mid,
            "incorporation_age": float(incorporation_age),
            "is_private_limited": is_pvt_ltd,
            "employee_count": employee_count,
            "pf_compliance_score": pf_compliance,
            "gstr_3b_delay_days": gstr_delay,
            "disposable_income_norm": disposable_inc_norm,
            "total_revenue_norm": float(total_revenue) / 1e7,
            "gst_liability_norm": float(gst_liability) / 1e6,
            "itc_available_norm": float(itc_available) / 1e6,
            "b2b_revenue_ratio": b2b_ratio,
            "export_revenue_ratio": export_ratio,
            "revenue_mean_norm": rev_mean,
            "revenue_std_norm": rev_std,
            "revenue_growth": float(rev_growth),
            "total_outstanding_norm": total_outstanding / 1e7,
            "total_sanctioned_norm": total_sanctioned / 1e7,
            "utilization_ratio": utilization_ratio,
            "overdue_ratio": overdue_ratio,
            "npa_count": npa_count,
            "sma_count": sma_count,
            "cc_accounts": cc_count,
            "od_accounts": od_count,
            "term_loan_accounts": tl_count,
            # Label columns
            "need_working_capital": need_wc,
            "need_machinery_capex": need_capex,
            "need_business_expansion": need_expansion,
            "need_inventory_funding": need_inventory,
            "need_trade_finance": need_trade,
            "need_digital_transformation": need_digital,
            "credit_risk_label": credit_risk,
        })

    df = pd.DataFrame(rows)
    print(f"  [OK] Built feature matrix: {df.shape[0]} rows × {df.shape[1]} columns")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Main Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def main(n_msmes: int = 10_000, seed: int = 42) -> None:
    print(f"\n{'='*60}")
    print(f"  MSME Pulse — Synthetic Data Generator")
    print(f"  MSMEs: {n_msmes:,} | Seed: {seed}")
    print(f"{'='*60}\n")

    # Seed for reproducibility
    rng = random.Random(seed)
    np.random.seed(seed)
    faker = Faker("en_IN")
    Faker.seed(seed)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}\n")

    # ── Step 1: Generate MSMEs ────────────────────────────────────────────
    print("Step 1/4 — Generating MSME profiles...")
    msmes = generate_msmes(n_msmes, rng, faker)

    # ── Step 2: Generate GST Returns ─────────────────────────────────────
    print("Step 2/4 — Generating GST returns...")
    gst_records = generate_gst_returns(msmes, rng)

    # ── Step 3: Generate AA Accounts ─────────────────────────────────────
    print("Step 3/4 — Generating AA accounts...")
    aa_records = generate_aa_accounts(msmes, rng)

    # ── Step 4: Build Feature Matrix ─────────────────────────────────────
    print("Step 4/4 — Building ML feature matrix...")
    feature_df = build_feature_matrix(msmes, gst_records, aa_records)

    # ── Save outputs ──────────────────────────────────────────────────────
    print("\nSaving outputs...")

    # Strip internal metadata fields before saving MSMEs
    clean_msmes = [
        {k: v for k, v in m.items() if not k.startswith("_")}
        for m in msmes
    ]

    msme_path = OUTPUT_DIR / "msmes.json"
    with open(msme_path, "w", encoding="utf-8") as f:
        json.dump(clean_msmes, f, ensure_ascii=False, default=str)
    print(f"  [OK] {msme_path} ({len(clean_msmes):,} records, {msme_path.stat().st_size / 1e6:.1f} MB)")

    gst_path = OUTPUT_DIR / "gst_returns.json"
    with open(gst_path, "w", encoding="utf-8") as f:
        json.dump(gst_records, f, ensure_ascii=False, default=str)
    print(f"  [OK] {gst_path} ({len(gst_records):,} records, {gst_path.stat().st_size / 1e6:.1f} MB)")

    aa_path = OUTPUT_DIR / "aa_accounts.json"
    with open(aa_path, "w", encoding="utf-8") as f:
        json.dump(aa_records, f, ensure_ascii=False, default=str)
    print(f"  [OK] {aa_path} ({len(aa_records):,} records, {aa_path.stat().st_size / 1e6:.1f} MB)")

    parquet_path = OUTPUT_DIR / "feature_matrix.parquet"
    feature_df.to_parquet(parquet_path, index=False)
    print(f"  [OK] {parquet_path} ({parquet_path.stat().st_size / 1e6:.1f} MB)")

    csv_path = OUTPUT_DIR / "feature_matrix.csv"
    feature_df.to_csv(csv_path, index=False)
    print(f"  [OK] {csv_path} ({csv_path.stat().st_size / 1e6:.1f} MB)")

    # ── Summary Statistics ────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  GENERATION COMPLETE — Summary Statistics")
    print(f"{'='*60}")

    # MSME stats
    status_counts = {}
    for m in clean_msmes:
        s = m["status"]
        status_counts[s] = status_counts.get(s, 0) + 1

    state_counts: dict[str, int] = {}
    for m in clean_msmes:
        s = m["state"]
        state_counts[s] = state_counts.get(s, 0) + 1

    print(f"\n  MSME Profiles: {len(clean_msmes):,}")
    print(f"    Status: {status_counts}")
    print(f"    Top states: {dict(sorted(state_counts.items(), key=lambda x: -x[1])[:5])}")

    print(f"\n  GST Returns: {len(gst_records):,}")
    filed = sum(1 for g in gst_records if g["filing_status"] == "FILED")
    print(f"    Filed: {filed:,} ({filed/len(gst_records)*100:.1f}%)")

    print(f"\n  AA Accounts: {len(aa_records):,}")
    npa = sum(1 for a in aa_records if a["repayment_status"] == "NPA")
    sma = sum(1 for a in aa_records if a["repayment_status"].startswith("SMA"))
    print(f"    NPA: {npa:,} ({npa/len(aa_records)*100:.1f}%)")
    print(f"    SMA: {sma:,} ({sma/len(aa_records)*100:.1f}%)")

    print(f"\n  Feature Matrix: {feature_df.shape[0]:,} × {feature_df.shape[1]} columns")
    label_cols = [c for c in feature_df.columns if c.startswith("need_") or c == "credit_risk_label"]
    for col in label_cols:
        pos = int(feature_df[col].sum())
        print(f"    {col}: {pos:,} positives ({pos/len(feature_df)*100:.1f}%)")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MSME Pulse Synthetic Data Generator")
    parser.add_argument("--msmes", type=int, default=10_000, help="Number of MSME profiles to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()
    main(n_msmes=args.msmes, seed=args.seed)
