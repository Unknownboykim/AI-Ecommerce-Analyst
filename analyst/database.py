"""
database.py
-----------
Load step and query runner. Uses SQLite so the project runs right after
cloning, with no database server to install.

    create_schema()  drops and recreates the five tables
    write_table()    appends a DataFrame to a table
    load_seed()      runs data/seed_data.sql
    run_sql()        runs a read-only query and returns a DataFrame
"""

import sqlite3
from pathlib import Path

import pandas as pd

from analyst.config import DB_PATH, SEED_SQL_PATH

TABLES = ["products", "product_reviews", "carts", "cart_items", "users"]

SCHEMA_SQL = """
CREATE TABLE products (
    id                   INTEGER PRIMARY KEY,
    title                TEXT,
    description          TEXT,
    category             TEXT,
    price                REAL,
    discountPercentage   REAL,
    rating               REAL,
    stock                INTEGER,
    brand                TEXT,
    sku                  TEXT,
    weight               INTEGER,
    availabilityStatus   TEXT,
    returnPolicy         TEXT,
    warrantyInformation  TEXT,
    minimumOrderQuantity INTEGER,
    thumbnail            TEXT,
    tags                 TEXT,
    dim_width            REAL,
    dim_height           REAL,
    dim_depth            REAL,
    meta_createdAt       TEXT,
    meta_updatedAt       TEXT,
    meta_barcode         TEXT
);

CREATE TABLE product_reviews (
    review_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id     INTEGER,
    rating         INTEGER,
    comment        TEXT,
    review_date    TEXT,
    reviewer_name  TEXT,
    reviewer_email TEXT
);

CREATE TABLE carts (
    id              INTEGER PRIMARY KEY,
    userId          INTEGER,
    total           REAL,
    discountedTotal REAL,
    totalProducts   INTEGER,
    totalQuantity   INTEGER
);

CREATE TABLE cart_items (
    item_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    cart_id            INTEGER,
    product_id         INTEGER,
    title              TEXT,
    price              REAL,
    quantity           INTEGER,
    total              REAL,
    discountPercentage REAL,
    discountedTotal    REAL,
    thumbnail          TEXT
);

CREATE TABLE users (
    id              INTEGER PRIMARY KEY,
    firstName       TEXT,
    lastName        TEXT,
    maidenName      TEXT,
    age             INTEGER,
    gender          TEXT,
    email           TEXT,
    phone           TEXT,
    username        TEXT,
    birthDate       TEXT,
    bloodGroup      TEXT,
    height          REAL,
    weight          REAL,
    eyeColor        TEXT,
    university      TEXT,
    role            TEXT,
    hair_color      TEXT,
    hair_type       TEXT,
    addr_street     TEXT,
    addr_city       TEXT,
    addr_state      TEXT,
    addr_postalCode TEXT,
    addr_country    TEXT,
    company_name    TEXT,
    company_dept    TEXT,
    company_title   TEXT,
    bank_cardType   TEXT,
    bank_currency   TEXT,
    bank_iban       TEXT
);
"""


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open a read/write connection, creating the data folder if needed."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def create_schema(conn: sqlite3.Connection) -> None:
    """Drop and recreate every table so each build starts clean."""
    for table in TABLES:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    print(f"SUCCESS: Created tables {', '.join(TABLES)}")


def write_table(conn: sqlite3.Connection, df: pd.DataFrame, table: str) -> int:
    """Append a DataFrame to an existing table. Returns rows written."""
    if df is None or df.empty:
        print(f"SKIPPED: No rows for {table}")
        return 0
    df.to_sql(table, conn, if_exists="append", index=False)
    conn.commit()
    print(f"SUCCESS: Wrote {len(df)} rows to {table}")
    return len(df)


def load_seed(conn: sqlite3.Connection, seed_path: Path = SEED_SQL_PATH) -> None:
    """Run the seed file that plants the anomalies the menu queries look for."""
    conn.executescript(seed_path.read_text(encoding="utf-8"))
    conn.commit()
    print(f"SUCCESS: Loaded seed data from {seed_path.name}")


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Row count for each table."""
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}


def run_sql(sql: str, db_path: Path = DB_PATH) -> pd.DataFrame:
    """
    Run one query against a read-only connection and return a DataFrame.
    Opening the file in read-only mode means a menu query can never change data.
    """
    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found at {db_path}. Run 'python build_database.py' first."
        )
    uri = f"file:{db_path.as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        return pd.read_sql_query(sql, conn)
