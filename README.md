# Ecommerce AI Analyst

A guided analytics tool for an ecommerce database. Users pick a business question from a menu, or type a few search terms, and get back the results table, a chart, and an optional written analysis from an LLM.

It is built on a full ETL pipeline: data is pulled from a public API, cleaned and flattened, loaded into SQLite, and topped up with synthetic data that plants 12 realistic problems (discount abuse, dead stock, duplicate SKUs, and more) for the analyst to find.

## Why a menu instead of a chatbot

Free text "chat with your data" tools look impressive in a demo, but they guess at what the user meant and write new SQL every time, so the same question can give different answers. This project takes the approach most real reporting tools use:

- **Every question is backed by a pre-written, reviewed SQL query.** The answer is correct and the same every time.
- **Users choose from a menu or search by terms**, so they always know what the tool can answer. Nothing is silently misread.
- **The LLM only explains results.** It never sees the database and never writes SQL. It receives the question and the rows the query returned, and is told to use only that data.
- **The database is opened read-only** for every menu query, so nothing a user does can change the data.

## How it works

```
DummyJSON API --> transform --> SQLite <-- seed_data.sql (planted anomalies)
                                  |
menu pick or search terms --> query catalog --> results table + chart
                                                        |
                                                        v
                                         OpenAI written analysis (optional)
```

| Step | File | What it does |
|---|---|---|
| Extract | `analyst/api_client.py` | Fetches products, carts, and users from dummyjson.com |
| Transform | `analyst/transformer.py` | Flattens nested JSON, splits reviews and cart items into their own tables, drops sensitive fields (passwords, SSNs, card numbers, IPs) |
| Load | `analyst/database.py` | Creates the five tables and writes the data to `data/ecommerce.db` |
| Seed | `data/seed_data.sql` | Adds synthetic users, products, carts, and reviews with planted anomalies |
| Catalog | `analyst/queries.py` | The 18 pre-written questions, each with its SQL, search keywords, and chart settings |
| Search | `analyst/search.py` | Ranks catalog questions against the terms a user types |
| Analysis | `analyst/llm.py` | Sends the question and result rows to OpenAI and returns a short write-up |
| Front ends | `menu.py`, `streamlit_app.py` | Terminal menu and web app, both calling `analyst/service.py` |

## The questions

**Products and Pricing**
- Average price by category
- Product count by category
- Price inconsistency within a category
- Rating vs price outliers

**Inventory**
- Low stock (under 20 units)
- Stockout risk (low stock, high demand)
- Dead stock (high stock, never ordered)

**Customers and Orders**
- Largest orders
- Average cart value
- Revenue concentration (top spenders)
- Discount abuse (over 50% off)
- High quantity carts
- Revenue by state
- Spend by age group

**Data Quality**
- Duplicate SKUs
- Products missing brand or category
- Orphaned reviews
- Data quality scorecard

### Planted anomalies

The seed data is designed so each of these has a known answer, which makes it easy to check the queries and the AI write-ups:

| Anomaly | Where it is planted |
|---|---|
| Revenue concentration | Users 111 to 113 own five large carts |
| Discount abuse | Carts 26 to 30 have 65% to 72% off |
| High quantity carts | Carts 48 to 50 have 17 to 22 items |
| Dead stock | Products 111 to 115 have 210 to 1,200 units and never appear in a cart |
| Stockout risk | Products 125 to 127 have 2 to 4 units but appear in many carts |
| Price inconsistency | Furniture ranges from a $12 stool to a $4,500 sofa |
| Rating vs price outliers | A $29.99 diamond bracelet rated 4.9, $899 sunglasses rated 1.9 |
| Duplicate SKUs | Products 101 and 120, and 103 and 121, share SKUs |
| Missing brand | Products 122, 123, and 129 |
| Missing category | Product 124 |
| Orphaned reviews | Reviews for product IDs 996 to 999, which do not exist |
| Geographic and age spread | Users across 15 states, ages 19 to 61 |

## Quick start

Requires Python 3.10 or newer.

```bash
git clone <your-repo-url>
cd ecommerce-ai-analyst
python -m venv .venv
```

Activate the environment (`.venv\Scripts\activate` on Windows, `source .venv/bin/activate` on Mac or Linux), then:

```bash
pip install -r requirements.txt
python build_database.py
```

`build_database.py` pulls the API data and loads the seed file. Use `python build_database.py --offline` to build from the seed data only, with no internet connection. If the API cannot be reached, the build falls back to seed data automatically.

### Turn on AI analysis (optional)

Copy `.env.example` to `.env` and add your OpenAI key:

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Without a key, everything still works. You get the tables and charts, just not the written analysis.

## Using it

### Web app

```bash
streamlit run streamlit_app.py
```

Pick a topic and question in the sidebar, or type terms like `discount`, `dead stock`, or `revenue by state` into the search box. Each answer shows the table, a chart, the SQL behind it, and an **Analyze these results** button.

If the database file does not exist yet, the app builds it on first launch.

### Terminal menu

```bash
python menu.py
```

Enter a menu number, or type search terms and pick from the matches. Other options:

```bash
python menu.py --list
```

```bash
python menu.py --run dead_stock
```

```bash
python menu.py --run discount_abuse --no-ai
```

## Adding a question

Every question lives in `analyst/queries.py`. To add one, append a `Query` to `CATALOG`:

```python
Query(
    key="top_rated_products",
    group="Products and Pricing",
    title="Top rated products",
    question="Which products have the highest customer ratings?",
    keywords=("top rated", "best", "rating", "reviews"),
    chart=("title", "rating"),
    sql="""
        SELECT title, category, rating, price
        FROM products
        ORDER BY rating DESC
        LIMIT 10;
    """,
),
```

The menu, search, web app, and tests pick it up automatically. Keywords with more than one word count double in search, so add a specific phrase when a question competes with similar ones.

## Tests

```bash
pytest
```

The tests build a seed-only database in a temp folder, so they need no internet and no API key. They check that:

- every catalog query runs and its chart columns exist
- each planted anomaly is found by the query meant to find it
- search returns the right question for common terms
- the query connection is read-only
- sensitive user fields are dropped during the transform

## Project structure

```
ecommerce-ai-analyst/
|-- analyst/
|   |-- api_client.py      Extract from DummyJSON
|   |-- transformer.py     Flatten JSON into tables
|   |-- database.py        Schema, loading, read-only query runner
|   |-- queries.py         The question catalog
|   |-- search.py          Search terms to questions
|   |-- llm.py             OpenAI analysis
|   |-- service.py         Runs a question end to end
|   `-- config.py          Settings from .env
|-- data/
|   `-- seed_data.sql      Synthetic data with planted anomalies
|-- tests/
|   `-- test_analyst.py
|-- build_database.py      ETL pipeline entry point
|-- menu.py                Terminal app
|-- streamlit_app.py       Web app
|-- requirements.txt
`-- .env.example
```

## Deploying

The web app runs on Streamlit Community Cloud as is:

1. Push the repo to GitHub. `.gitignore` already keeps `.env` and the database file out.
2. Create a new app on share.streamlit.io pointing at `streamlit_app.py`.
3. Add `OPENAI_API_KEY` under the app's Secrets if you want AI analysis.

The database is built on first launch.

## Data and privacy notes

- All data is either public sample data from dummyjson.com or synthetic. No real customer data is used.
- The transform step drops passwords, SSNs, EINs, IP and MAC addresses, user agents, crypto wallets, and full card numbers before anything is stored.
- API carts are limited to 20 and line items are kept only for fetched products, so the API data never collides with the seeded IDs.
- Only the question and the query result rows (capped at 50) are sent to OpenAI.

## Skills shown

ETL pipeline design, JSON flattening, relational schema design, SQL (joins, CTEs, window functions, data quality checks), anomaly detection, LLM integration with grounded prompts, Streamlit, automated testing.
