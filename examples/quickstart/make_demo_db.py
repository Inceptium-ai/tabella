"""Create the quickstart demo database (retail.db): customers + orders."""

import sqlite3
from pathlib import Path

DB = Path(__file__).parent / "retail.db"

DDL = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL,
    full_name TEXT NOT NULL,
    country TEXT,
    created_at DATETIME NOT NULL
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    total REAL NOT NULL,
    status TEXT NOT NULL,
    placed_at DATETIME NOT NULL
);
"""

CUSTOMERS = [
    (1, "amelie@example.com", "Amelie Fournier", "FR", "2025-11-02 09:15:00"),
    (2, "jonas@example.com", "Jonas Weber", "DE", "2025-11-05 14:20:00"),
    (3, "sofia@example.com", "Sofia Rossi", "IT", "2025-12-01 11:05:00"),
    (4, "lena@example.com", "Lena Schmidt", "DE", "2026-01-18 16:40:00"),
]

ORDERS = [
    (1, 1, 129.90, "shipped", "2026-01-03 10:00:00"),
    (2, 2, 42.50, "delivered", "2026-01-04 12:30:00"),
    (3, 2, 310.00, "processing", "2026-02-11 09:45:00"),
    (4, 3, 18.75, "delivered", "2026-02-14 15:10:00"),
    (5, 4, 77.30, "shipped", "2026-03-02 08:20:00"),
]


def main() -> None:
    DB.unlink(missing_ok=True)
    with sqlite3.connect(DB) as conn:
        conn.executescript(DDL)
        conn.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?)", CUSTOMERS)
        conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", ORDERS)
    print(f"created {DB} ({len(CUSTOMERS)} customers, {len(ORDERS)} orders)")


if __name__ == "__main__":
    main()
