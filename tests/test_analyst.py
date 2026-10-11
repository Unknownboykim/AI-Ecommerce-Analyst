"""
Tests run against a seed-only database built in a temp folder, so they need
no internet and no API key.

    pytest
"""

import pandas as pd
import pytest

from analyst import database, llm
from analyst.queries import CATALOG, QUERIES_BY_KEY, get_query
from analyst.search import search
from analyst.transformer import transform_carts, transform_users


@pytest.fixture(scope="session")
def db_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("db") / "test.db"
    with database.connect(path) as conn:
        database.create_schema(conn)
        database.load_seed(conn)
    return path


def run(key, db_path):
    return database.run_sql(get_query(key).sql, db_path)


# ------------------------------------------------------------------ catalog

def test_every_query_runs(db_path):
    for q in CATALOG:
        df = database.run_sql(q.sql, db_path)
        assert isinstance(df, pd.DataFrame), q.key


def test_query_keys_are_unique():
    assert len(QUERIES_BY_KEY) == len(CATALOG)


def test_chart_columns_exist(db_path):
    for q in CATALOG:
        if q.chart:
            df = database.run_sql(q.sql, db_path)
            assert set(q.chart) <= set(df.columns), q.key


def test_unknown_key_raises():
    with pytest.raises(KeyError):
        get_query("not_a_query")


# ------------------------------------------------------------------ planted anomalies are found

def test_dead_stock(db_path):
    assert set(run("dead_stock", db_path)["id"]) >= {111, 112, 113, 114, 115}


def test_stockout_risk(db_path):
    assert {125, 126, 127} <= set(run("stockout_risk", db_path)["id"])


def test_discount_abuse(db_path):
    assert {26, 27, 28, 29, 30} <= set(run("discount_abuse", db_path)["cart_id"])


def test_duplicate_skus(db_path):
    assert {"PSX1-2024", "FRN-SNKM"} <= set(run("duplicate_skus", db_path)["sku"])


def test_missing_fields(db_path):
    assert {122, 123, 124, 129} <= set(run("missing_product_fields", db_path)["id"])


def test_orphaned_reviews(db_path):
    df = run("orphaned_reviews", db_path)
    assert not df.empty
    assert (df["product_id"] >= 996).all()


def test_rating_price_outliers(db_path):
    assert {116, 118} <= set(run("rating_price_outliers", db_path)["id"])


def test_high_quantity_carts(db_path):
    assert {48, 49, 50} <= set(run("high_quantity_carts", db_path)["cart_id"])


def test_revenue_concentration_whales_on_top(db_path):
    df = run("revenue_concentration", db_path)
    assert df["pct_of_revenue"].iloc[0] >= df["pct_of_revenue"].iloc[-1]
    assert df["cumulative_pct"].iloc[-1] <= 100


def test_database_is_read_only(db_path):
    with pytest.raises(Exception):
        database.run_sql("DELETE FROM products", db_path)


# ------------------------------------------------------------------ search

@pytest.mark.parametrize("terms, expected", [
    ("discount abuse", "discount_abuse"),
    ("dead stock", "dead_stock"),
    ("low stock", "low_stock_products"),
    ("duplicate sku", "duplicate_skus"),
    ("orphaned reviews", "orphaned_reviews"),
    ("revenue by state", "customers_by_state"),
    ("spend by age group", "spend_by_age_group"),
    ("which items are overpriced", "rating_price_outliers"),
])
def test_search_top_result(terms, expected):
    assert search(terms)[0].key == expected


def test_search_no_match():
    assert search("what is the weather today") == []
    assert search("   ") == []


def test_age_does_not_match_average():
    assert "spend_by_age_group" not in [q.key for q in search("average")]


# ------------------------------------------------------------------ transformer and llm helpers

def test_users_drop_sensitive_fields():
    raw = [{"id": 1, "firstName": "A", "password": "x", "ssn": "1", "bank": {"cardNumber": "4111", "cardType": "Visa"}}]
    df = transform_users(raw)
    assert "password" not in df.columns and "ssn" not in df.columns
    assert "bank_cardNumber" not in df.columns
    assert df.loc[0, "bank_cardType"] == "Visa"


def test_cart_items_filtered_to_known_products():
    raw = [{"id": 1, "userId": 1, "products": [{"id": 5}, {"id": 150}]}]
    _, items = transform_carts(raw, known_product_ids={5})
    assert list(items["product_id"]) == [5]


def test_llm_clean_text_removes_dashes():
    assert "\u2014" not in llm.clean_text("Revenue rose \u2014 sharply")


def test_format_table_truncates():
    df = pd.DataFrame({"n": range(100)})
    assert "more rows not shown" in llm.format_table(df, max_rows=10)
