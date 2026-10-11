"""
queries.py
----------
The query catalog. Every question the app can answer lives here as a
pre-written, reviewed SQL query. Users pick from the menu or search by
terms; the app never writes SQL on the fly, so results are predictable,
fast, and safe.

To add a question: append a Query to CATALOG. The menu, the search, the
Streamlit app, and the tests all pick it up automatically.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Query:
    key: str                 # stable id, used by the CLI and tests
    group: str               # menu section
    title: str               # short menu label
    question: str            # the business question, also sent to the LLM
    sql: str
    keywords: tuple[str, ...] = field(default_factory=tuple)  # search terms
    chart: tuple[str, str] | None = None                       # (x column, y column)


GROUPS = [
    "Products and Pricing",
    "Inventory",
    "Customers and Orders",
    "Data Quality",
]

CATALOG: list[Query] = [
    # ---------------------------------------------------------------- Products and Pricing
    Query(
        key="highest_avg_price_category",
        group="Products and Pricing",
        title="Average price by category",
        question="Which product category has the highest average price?",
        keywords=("average price", "expensive", "category", "price", "cost"),
        chart=("category", "avg_price"),
        sql="""
            SELECT
                COALESCE(category, '(missing)') AS category,
                ROUND(AVG(price), 2)            AS avg_price,
                COUNT(*)                        AS product_count
            FROM products
            GROUP BY category
            ORDER BY avg_price DESC;
        """,
    ),
    Query(
        key="most_products_by_category",
        group="Products and Pricing",
        title="Product count by category",
        question="Which category has the most products?",
        keywords=("how many", "count", "category", "catalog", "products"),
        chart=("category", "product_count"),
        sql="""
            SELECT
                COALESCE(category, '(missing)') AS category,
                COUNT(*)                        AS product_count,
                ROUND(MIN(price), 2)            AS min_price,
                ROUND(MAX(price), 2)            AS max_price
            FROM products
            GROUP BY category
            ORDER BY product_count DESC;
        """,
    ),
    Query(
        key="price_spread_by_category",
        group="Products and Pricing",
        title="Price inconsistency within a category",
        question="Which categories have the widest price spread between their cheapest and most expensive product?",
        keywords=("inconsistent", "inconsistency", "spread", "range", "price", "category", "variance"),
        chart=("category", "max_to_min_ratio"),
        sql="""
            SELECT
                category,
                COUNT(*)                            AS product_count,
                ROUND(MIN(price), 2)                AS min_price,
                ROUND(MAX(price), 2)                AS max_price,
                ROUND(MAX(price) / MIN(price), 1)   AS max_to_min_ratio
            FROM products
            WHERE category IS NOT NULL AND price > 0
            GROUP BY category
            HAVING COUNT(*) >= 3
            ORDER BY max_to_min_ratio DESC
            LIMIT 10;
        """,
    ),
    Query(
        key="rating_price_outliers",
        group="Products and Pricing",
        title="Rating vs price outliers",
        question="Which products look mispriced: very highly rated but cheap, or poorly rated but expensive?",
        keywords=("mispriced", "outlier", "underpriced", "overpriced", "rating", "price", "value"),
        sql="""
            SELECT
                id, title, category, brand,
                price, rating,
                CASE
                    WHEN rating >= 4.8 AND price < 50   THEN 'Possibly underpriced'
                    WHEN rating <= 2.0 AND price >= 300 THEN 'Possibly overpriced'
                END AS flag
            FROM products
            WHERE (rating >= 4.8 AND price < 50)
               OR (rating <= 2.0 AND price >= 300)
            ORDER BY flag, price DESC;
        """,
    ),
    # ---------------------------------------------------------------- Inventory
    Query(
        key="low_stock_products",
        group="Inventory",
        title="Low stock (under 20 units)",
        question="Which products have low stock (under 20 units)?",
        keywords=("low stock", "stock", "inventory", "running out", "restock"),
        sql="""
            SELECT title, category, brand, stock, price, rating
            FROM products
            WHERE stock < 20
            ORDER BY stock ASC;
        """,
    ),
    Query(
        key="stockout_risk",
        group="Inventory",
        title="Stockout risk (low stock, high demand)",
        question="Which products have very little stock left but keep appearing in customer carts?",
        keywords=("stockout", "stock out", "demand", "sell out", "stock", "risk", "inventory"),
        chart=("title", "carts_containing"),
        sql="""
            SELECT
                p.id,
                p.title,
                p.category,
                p.stock,
                COUNT(DISTINCT ci.cart_id) AS carts_containing,
                SUM(ci.quantity)           AS units_in_carts
            FROM products p
            JOIN cart_items ci ON ci.product_id = p.id
            WHERE p.stock <= 5
            GROUP BY p.id, p.title, p.category, p.stock
            ORDER BY carts_containing DESC, p.stock ASC;
        """,
    ),
    Query(
        key="dead_stock",
        group="Inventory",
        title="Dead stock (high stock, never ordered)",
        question="Which products have a lot of stock but have never appeared in a cart?",
        keywords=("dead stock", "unsold", "never sold", "overstock", "slow moving", "stock", "inventory"),
        chart=("title", "stock"),
        sql="""
            SELECT
                p.id, p.title, p.category, p.brand,
                p.stock, p.price,
                ROUND(p.stock * p.price, 2) AS inventory_value,
                p.rating
            FROM products p
            LEFT JOIN cart_items ci ON ci.product_id = p.id
            WHERE ci.product_id IS NULL
              AND p.stock >= 200
            ORDER BY inventory_value DESC;
        """,
    ),
    # ---------------------------------------------------------------- Customers and Orders
    Query(
        key="largest_orders_by_user",
        group="Customers and Orders",
        title="Largest orders",
        question="Which users have placed the largest orders by total value?",
        keywords=("largest", "biggest", "order", "cart", "user", "customer", "top"),
        sql="""
            SELECT
                c.id                        AS cart_id,
                u.firstName || ' ' || u.lastName AS customer,
                u.addr_city                 AS city,
                u.addr_state                AS state,
                ROUND(c.total, 2)           AS cart_total,
                ROUND(c.discountedTotal, 2) AS discounted_total,
                c.totalQuantity             AS items
            FROM carts c
            JOIN users u ON u.id = c.userId
            ORDER BY c.total DESC
            LIMIT 10;
        """,
    ),
    Query(
        key="average_cart_total",
        group="Customers and Orders",
        title="Average cart value",
        question="What is the average cart total across all orders?",
        keywords=("average", "avg", "aov", "order value", "cart", "basket"),
        sql="""
            SELECT
                COUNT(*)                       AS total_carts,
                ROUND(AVG(total), 2)           AS avg_cart_total,
                ROUND(AVG(discountedTotal), 2) AS avg_discounted_total,
                ROUND(AVG(totalQuantity), 1)   AS avg_items_per_cart
            FROM carts;
        """,
    ),
    Query(
        key="revenue_concentration",
        group="Customers and Orders",
        title="Revenue concentration (top spenders)",
        question="How much of total revenue comes from the top spending customers?",
        keywords=("revenue", "concentration", "whale", "top spender", "share", "spend", "customer"),
        chart=("customer", "revenue"),
        sql="""
            WITH spend AS (
                SELECT
                    u.id,
                    u.firstName || ' ' || u.lastName AS customer,
                    COUNT(c.id)                      AS carts,
                    SUM(c.discountedTotal)           AS revenue
                FROM carts c
                JOIN users u ON u.id = c.userId
                GROUP BY u.id, customer
            )
            SELECT
                customer,
                carts,
                ROUND(revenue, 2) AS revenue,
                ROUND(100.0 * revenue / SUM(revenue) OVER (), 1) AS pct_of_revenue,
                ROUND(100.0 * SUM(revenue) OVER (ORDER BY revenue DESC)
                      / SUM(revenue) OVER (), 1)                  AS cumulative_pct
            FROM spend
            ORDER BY revenue DESC
            LIMIT 10;
        """,
    ),
    Query(
        key="discount_abuse",
        group="Customers and Orders",
        title="Discount abuse (over 50% off)",
        question="Are there any orders with suspiciously large discounts (more than 50% off)?",
        keywords=("discount", "abuse", "coupon", "promo", "fraud", "markdown"),
        chart=("cart_id", "discount_pct"),
        sql="""
            SELECT
                c.id                              AS cart_id,
                u.firstName || ' ' || u.lastName  AS customer,
                ROUND(c.total, 2)                 AS cart_total,
                ROUND(c.discountedTotal, 2)       AS discounted_total,
                ROUND(100.0 * (1 - c.discountedTotal / c.total), 1) AS discount_pct
            FROM carts c
            LEFT JOIN users u ON u.id = c.userId
            WHERE c.total > 0
              AND (1 - c.discountedTotal / c.total) > 0.5
            ORDER BY discount_pct DESC;
        """,
    ),
    Query(
        key="high_quantity_carts",
        group="Customers and Orders",
        title="High quantity carts",
        question="Which carts have an unusually high number of items (15 or more)?",
        keywords=("quantity", "bulk", "abandoned", "many items", "large cart", "units"),
        sql="""
            SELECT
                c.id                              AS cart_id,
                u.firstName || ' ' || u.lastName  AS customer,
                c.totalProducts                   AS distinct_products,
                c.totalQuantity                   AS total_units,
                ROUND(c.total, 2)                 AS cart_total
            FROM carts c
            LEFT JOIN users u ON u.id = c.userId
            WHERE c.totalQuantity >= 15
            ORDER BY c.totalQuantity DESC;
        """,
    ),
    Query(
        key="customers_by_state",
        group="Customers and Orders",
        title="Revenue by state",
        question="Which states generate the most revenue and how many customers are in each?",
        keywords=("state", "by state", "region", "geography", "location", "where", "geo"),
        chart=("state", "revenue"),
        sql="""
            SELECT
                u.addr_state                AS state,
                COUNT(DISTINCT u.id)        AS customers,
                COUNT(c.id)                 AS carts,
                ROUND(SUM(c.discountedTotal), 2) AS revenue
            FROM users u
            JOIN carts c ON c.userId = u.id
            GROUP BY u.addr_state
            ORDER BY revenue DESC;
        """,
    ),
    Query(
        key="spend_by_age_group",
        group="Customers and Orders",
        title="Spend by age group",
        question="How does spending differ across customer age groups?",
        keywords=("age", "age group", "by age", "demographic", "generation", "segment"),
        chart=("age_group", "revenue"),
        sql="""
            SELECT
                CASE
                    WHEN u.age < 25 THEN '18-24'
                    WHEN u.age < 35 THEN '25-34'
                    WHEN u.age < 45 THEN '35-44'
                    WHEN u.age < 55 THEN '45-54'
                    ELSE '55+'
                END                                  AS age_group,
                COUNT(DISTINCT u.id)                 AS customers,
                COUNT(c.id)                          AS carts,
                ROUND(SUM(c.discountedTotal), 2)     AS revenue,
                ROUND(AVG(c.discountedTotal), 2)     AS avg_cart
            FROM users u
            JOIN carts c ON c.userId = u.id
            GROUP BY age_group
            ORDER BY age_group;
        """,
    ),
    # ---------------------------------------------------------------- Data Quality
    Query(
        key="duplicate_skus",
        group="Data Quality",
        title="Duplicate SKUs",
        question="Are any SKUs used by more than one product?",
        keywords=("duplicate", "sku", "dupe", "repeated", "data quality"),
        sql="""
            SELECT
                p.sku,
                p.id,
                p.title,
                p.price
            FROM products p
            JOIN (
                SELECT sku FROM products
                WHERE sku IS NOT NULL
                GROUP BY sku
                HAVING COUNT(*) > 1
            ) d ON d.sku = p.sku
            ORDER BY p.sku, p.id;
        """,
    ),
    Query(
        key="missing_product_fields",
        group="Data Quality",
        title="Products missing brand or category",
        question="Which products are missing a brand or a category?",
        keywords=("missing", "null", "blank", "brand", "category", "incomplete", "data quality"),
        sql="""
            SELECT
                id, title,
                COALESCE(category, '(missing)') AS category,
                COALESCE(brand, '(missing)')    AS brand,
                CASE
                    WHEN category IS NULL AND brand IS NULL THEN 'brand and category'
                    WHEN category IS NULL                   THEN 'category'
                    ELSE 'brand'
                END AS missing_field
            FROM products
            WHERE brand IS NULL OR category IS NULL
            ORDER BY missing_field DESC, id;
        """,
    ),
    Query(
        key="orphaned_reviews",
        group="Data Quality",
        title="Orphaned reviews",
        question="Are there reviews that point to products that do not exist?",
        keywords=("orphan", "orphaned", "review", "broken", "foreign key", "data quality"),
        sql="""
            SELECT
                r.review_id,
                r.product_id,
                r.rating,
                r.reviewer_name,
                r.comment
            FROM product_reviews r
            LEFT JOIN products p ON p.id = r.product_id
            WHERE p.id IS NULL
            ORDER BY r.product_id;
        """,
    ),
    Query(
        key="data_quality_summary",
        group="Data Quality",
        title="Data quality scorecard",
        question="Give me an overall summary of data quality issues in the database.",
        keywords=("summary", "scorecard", "overview", "health", "issues", "data quality"),
        chart=("check_name", "issue_count"),
        sql="""
            SELECT 'Products missing brand' AS check_name,
                   COUNT(*) AS issue_count
            FROM products WHERE brand IS NULL
            UNION ALL
            SELECT 'Products missing category', COUNT(*)
            FROM products WHERE category IS NULL
            UNION ALL
            SELECT 'Products sharing a SKU', COUNT(*)
            FROM products
            WHERE sku IN (SELECT sku FROM products GROUP BY sku HAVING COUNT(*) > 1)
            UNION ALL
            SELECT 'Orphaned reviews', COUNT(*)
            FROM product_reviews r
            LEFT JOIN products p ON p.id = r.product_id
            WHERE p.id IS NULL
            UNION ALL
            SELECT 'Carts with no matching user', COUNT(*)
            FROM carts c
            LEFT JOIN users u ON u.id = c.userId
            WHERE u.id IS NULL;
        """,
    ),
]

QUERIES_BY_KEY: dict[str, Query] = {q.key: q for q in CATALOG}


def get_query(key: str) -> Query:
    """Look up a query by key, with a helpful error for unknown keys."""
    try:
        return QUERIES_BY_KEY[key]
    except KeyError:
        raise KeyError(f"Unknown query key '{key}'. Available: {', '.join(QUERIES_BY_KEY)}") from None


def queries_in_group(group: str) -> list[Query]:
    """All queries in one menu section, in catalog order."""
    return [q for q in CATALOG if q.group == group]
