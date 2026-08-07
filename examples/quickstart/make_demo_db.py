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
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    opened_at DATETIME NOT NULL
);
"""

TICKETS = [
    (1, 2, "Package arrived damaged",
     "The box was crushed on delivery and the mug inside is chipped. "
     "I would like a replacement shipped to the same address.", "2026-02-12 09:00:00"),
    (2, 1, "Cannot reset my password",
     "The password reset email never arrives even after checking spam. "
     "My account uses the amelie@example.com address.", "2026-02-20 15:30:00"),
    (3, 4, "Question about invoice VAT",
     "The March invoice does not show the German VAT breakdown our finance "
     "team needs for reporting. Can you reissue it with VAT details?", "2026-03-05 11:45:00"),
]

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
        conn.executemany("INSERT INTO tickets VALUES (?, ?, ?, ?, ?)", TICKETS)
    print(
        f"created {DB} ({len(CUSTOMERS)} customers, {len(ORDERS)} orders,"
        f" {len(TICKETS)} tickets)"
    )


if __name__ == "__main__":
    main()
