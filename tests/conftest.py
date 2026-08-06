import sqlite3
from pathlib import Path

import pytest
import udap_connectors  # noqa: F401  (registers built-in connectors)
from udap_core.models import (
    AssetMeta,
    Contract,
    ContractField,
    FieldType,
    OnboardingManifest,
    SourceRef,
)

DDL = """
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL,
    full_name TEXT NOT NULL,
    country TEXT,
    created_at DATETIME NOT NULL
);
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    total REAL NOT NULL,
    status TEXT NOT NULL
);
"""

ROWS = {
    "customers": [
        (1, "a@example.com", "Ada Lovelace", "GB", "2026-01-01 10:00:00"),
        (2, "b@example.com", "Blaise Pascal", "FR", "2026-01-02 11:00:00"),
        (3, "c@example.com", "Carl Gauss", "DE", "2026-01-03 12:00:00"),
    ],
    "orders": [
        (1, 1, 10.5, "shipped"),
        (2, 2, 20.0, "delivered"),
        (3, 2, 30.25, "processing"),
    ],
}


@pytest.fixture
def demo_db(tmp_path: Path) -> str:
    """Create a demo sqlite db; returns its UDAP source URI."""
    db = tmp_path / "retail.db"
    with sqlite3.connect(db) as conn:
        conn.executescript(DDL)
        conn.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?)", ROWS["customers"])
        conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", ROWS["orders"])
    return f"sqlite:///{db}"


@pytest.fixture
def customers_manifest(demo_db: str) -> OnboardingManifest:
    return OnboardingManifest(
        asset=AssetMeta(
            name="customers",
            description="Customer master records",
            owner="sales-data@example.com",
            domain="sales",
            tags=["crm"],
        ),
        source=SourceRef(connector="sqlite", uri=demo_db, native_name="customers"),
        contract=Contract(
            fields=[
                ContractField(name="id", type=FieldType.integer, required=True),
                ContractField(name="email", type=FieldType.string, required=True, pii=True),
                ContractField(name="full_name", pii=True),
            ]
        ),
    )
