"""
MSME Pulse — Database Seeder
============================
Reads the generated synthetic data JSON files and loads them into PostgreSQL.

Usage:
  python scripts/data_generation/seed_db.py [--drop]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import uuid

# Add backend directory to Python path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.append(str(PROJECT_ROOT / "backend"))

from app.database import engine, Base, AsyncSessionLocal
from app.models import MSME, GSTReturn, AAAccount, MSMEStatus

def parse_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")

async def seed_database(drop_tables: bool = False):
    print("\n" + "="*60)
    print("  MSME Pulse — Seeding Database")
    print("="*60 + "\n")

    # 1. Handle table recreation
    async with engine.begin() as conn:
        if drop_tables:
            print("Dropping existing database tables...")
            await conn.run_sync(Base.metadata.drop_all)
            print("  [OK] Tables dropped")
        
        print("Creating database tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("  [OK] Tables verified/created")

    # 2. Paths to data files
    data_dir = PROJECT_ROOT / "synthetic_data"
    msmes_file = data_dir / "msmes.json"
    gst_file = data_dir / "gst_returns.json"
    aa_file = data_dir / "aa_accounts.json"

    if not msmes_file.exists():
        print(f"ERROR: {msmes_file} not found. Please run generate_synthetic_data.py first.")
        return

    # 3. Read data
    print("\nReading synthetic data files...")
    with open(msmes_file, "r", encoding="utf-8") as f:
        msmes_data = json.load(f)
    print(f"  [OK] Loaded {len(msmes_data):,} MSME profiles")

    gst_data = []
    if gst_file.exists():
        with open(gst_file, "r", encoding="utf-8") as f:
            gst_data = json.load(f)
        print(f"  [OK] Loaded {len(gst_data):,} GST return records")

    aa_data = []
    if aa_file.exists():
        with open(aa_file, "r", encoding="utf-8") as f:
            aa_data = json.load(f)
        print(f"  [OK] Loaded {len(aa_data):,} AA account records")

    # 4. Insert into database
    async with AsyncSessionLocal() as session:
        # Load MSMEs
        print("\nSeeding MSME profiles...")
        count = 0
        for m in msmes_data:
            msme = MSME(
                id=uuid.UUID(m["id"]),
                gstin=m["gstin"],
                pan=m["pan"],
                cin=m["cin"],
                legal_name=m["legal_name"],
                trade_name=m["trade_name"],
                address_line1=m.get("address_line1"),
                address_line2=m.get("address_line2"),
                city=m.get("city"),
                state=m.get("state"),
                pincode=m.get("pincode"),
                nic_code=m.get("nic_code"),
                nic_description=m.get("nic_description"),
                incorporation_date=parse_date(m.get("incorporation_date")),
                constitution=m.get("constitution"),
                status=MSMEStatus(m["status"]),
                gst_registration_date=parse_date(m.get("gst_registration_date")),
                epfo_active_employees=int(m.get("epfo_active_employees", 0)),
                pf_compliance_score=float(m.get("pf_compliance_score", 0.0)),
                avg_monthly_inflow=float(m.get("avg_monthly_inflow", 0.0)),
                avg_monthly_outflow=float(m.get("avg_monthly_outflow", 0.0)),
                disposable_income=float(m.get("disposable_income", 0.0)),
                gstr_3b_delay_days=int(m.get("gstr_3b_delay_days", 0)),
                behavioral_tag=m.get("behavioral_tag", ""),
                created_at=parse_date(m.get("created_at")),
                updated_at=parse_date(m.get("updated_at")),
            )
            session.add(msme)
            count += 1
            if count % 1000 == 0:
                await session.flush()
                print(f"  .. flushed {count} MSMEs")

        await session.commit()
        print(f"  [OK] Seeded {count} MSMEs successfully!")

        # Load GST Returns
        if gst_data:
            print("\nSeeding GST returns...")
            count = 0
            for g in gst_data:
                ret = GSTReturn(
                    id=uuid.UUID(g["id"]),
                    msme_id=uuid.UUID(g["msme_id"]),
                    return_type=g["return_type"],
                    financial_year=g["financial_year"],
                    tax_period=g["tax_period"],
                    b2b_invoices=g.get("b2b_invoices", {}),
                    b2c_invoices=g.get("b2c_invoices", {}),
                    export_invoices=g.get("export_invoices", {}),
                    credit_debit_notes=g.get("credit_debit_notes", {}),
                    hsn_summary=g.get("hsn_summary", {}),
                    doc_issued=g.get("doc_issued", {}),
                    outward_supplies=float(g.get("outward_supplies", 0)),
                    inward_supplies=float(g.get("inward_supplies", 0)),
                    taxable_value=float(g.get("taxable_value", 0)),
                    igst=float(g.get("igst", 0)),
                    cgst=float(g.get("cgst", 0)),
                    sgst=float(g.get("sgst", 0)),
                    cess=float(g.get("cess", 0)),
                    itc_claimed=float(g.get("itc_claimed", 0)),
                    itc_reversed=float(g.get("itc_reversed", 0)),
                    net_tax_payable=float(g.get("net_tax_payable", 0)),
                    tax_paid=float(g.get("tax_paid", 0)),
                    total_revenue=float(g.get("total_revenue", 0)),
                    b2b_revenue=float(g.get("b2b_revenue", 0)),
                    b2c_revenue=float(g.get("b2c_revenue", 0)),
                    export_revenue=float(g.get("export_revenue", 0)),
                    gst_liability=float(g.get("gst_liability", 0)),
                    itc_available=float(g.get("itc_available", 0)),
                    filing_date=parse_date(g.get("filing_date")),
                    filing_status=g["filing_status"],
                    created_at=parse_date(g.get("created_at")),
                )
                session.add(ret)
                count += 1
                if count % 5000 == 0:
                    await session.flush()
                    print(f"  .. flushed {count} GST returns")

            await session.commit()
            print(f"  [OK] Seeded {count} GST returns successfully!")

        # Load AA Accounts
        if aa_data:
            print("\nSeeding Account Aggregator accounts...")
            count = 0
            for a in aa_data:
                acct = AAAccount(
                    id=uuid.UUID(a["id"]),
                    msme_id=uuid.UUID(a["msme_id"]),
                    fi_type=a["fi_type"],
                    fi_name=a["fi_name"],
                    account_type=a["account_type"],
                    account_number_masked=a["account_number_masked"],
                    sanctioned_limit=float(a.get("sanctioned_limit", 0)),
                    outstanding_amount=float(a.get("outstanding_amount", 0)),
                    drawing_power=float(a.get("drawing_power", 0)),
                    interest_rate=float(a.get("interest_rate", 0)),
                    repayment_status=a["repayment_status"],
                    days_past_due=int(a.get("days_past_due", 0)),
                    overdue_amount=float(a.get("overdue_amount", 0)),
                    account_open_date=parse_date(a.get("account_open_date")),
                    last_review_date=parse_date(a.get("last_review_date")),
                    maturity_date=parse_date(a.get("maturity_date")),
                    consent_id=a.get("consent_id"),
                    consent_status=a.get("consent_status"),
                    consent_start=parse_date(a.get("consent_start")),
                    consent_expiry=parse_date(a.get("consent_expiry")),
                    data_as_of=parse_date(a.get("data_as_of")),
                    fetched_at=parse_date(a.get("fetched_at")),
                )
                session.add(acct)
                count += 1
                if count % 2000 == 0:
                    await session.flush()
                    print(f"  .. flushed {count} AA accounts")

            await session.commit()
            print(f"  [OK] Seeded {count} AA accounts successfully!")

    print("\n" + "="*60)
    print("  SEEDING COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MSME Pulse Database Seeder")
    parser.add_argument("--drop", action="store_true", help="Drop all tables and recreate them before seeding")
    args = parser.parse_args()

    # Run the async seeder
    asyncio.run(seed_database(drop_tables=args.drop))
