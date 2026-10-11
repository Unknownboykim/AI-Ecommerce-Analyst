"""
build_database.py
-----------------
Runs the full ETL pipeline and builds data/ecommerce.db.

    1. Create the five tables (drops old ones first)
    2. Extract products, carts, and users from the DummyJSON API
    3. Transform the JSON into flat tables and drop sensitive fields
    4. Load the tables into SQLite
    5. Load data/seed_data.sql, which plants the anomalies the menu finds

Usage:
    python build_database.py            # API data plus seed data
    python build_database.py --offline  # seed data only, no internet needed

If the API cannot be reached, the build falls back to seed data only.
"""

import argparse
import sys

from analyst import api_client, database, transformer
from analyst.config import DB_PATH


def load_api_data(conn) -> bool:
    """Extract, transform, and load the API data. Returns False if any fetch failed."""
    print("\nSTEP 2: Extracting data from the DummyJSON API")
    products_raw = api_client.fetch_products()
    carts_raw = api_client.fetch_carts()
    users_raw = api_client.fetch_users()

    if products_raw is None or carts_raw is None or users_raw is None:
        return False

    print("\nSTEP 3: Transforming JSON into tables")
    df_products, df_reviews = transformer.transform_products(products_raw)
    known_ids = set(df_products["id"]) if not df_products.empty else set()
    df_carts, df_cart_items = transformer.transform_carts(carts_raw, known_product_ids=known_ids)
    df_users = transformer.transform_users(users_raw)

    print("\nSTEP 4: Loading tables into SQLite")
    database.write_table(conn, df_products, "products")
    database.write_table(conn, df_reviews, "product_reviews")
    database.write_table(conn, df_carts, "carts")
    database.write_table(conn, df_cart_items, "cart_items")
    database.write_table(conn, df_users, "users")
    return True


def build(offline: bool = False) -> None:
    print("=" * 50)
    print("  ECOMMERCE ETL PIPELINE")
    print("=" * 50)

    with database.connect() as conn:
        print("\nSTEP 1: Creating tables")
        database.create_schema(conn)

        if offline:
            print("\nSTEPS 2 to 4 skipped: offline mode, using seed data only")
        elif not load_api_data(conn):
            print("\nWARNING: API unavailable. Rebuilding with seed data only.")
            database.create_schema(conn)

        print("\nSTEP 5: Loading seed data with planted anomalies")
        database.load_seed(conn)

        counts = database.table_counts(conn)

    print("\n" + "=" * 50)
    print(f"  DONE: {DB_PATH}")
    print("=" * 50)
    for table, n in counts.items():
        print(f"  {table:<16}{n:>6} rows")
    print(f"  {'total':<16}{sum(counts.values()):>6} rows")
    print("\nNext: python menu.py   or   streamlit run streamlit_app.py")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the ecommerce SQLite database.")
    parser.add_argument("--offline", action="store_true", help="skip the API and load seed data only")
    args = parser.parse_args()

    try:
        build(offline=args.offline)
    except Exception as e:
        print(f"\nPIPELINE FAILED: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
