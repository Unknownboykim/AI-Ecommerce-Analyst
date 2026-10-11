"""
api_client.py
-------------
Extract step. Calls the DummyJSON endpoints and returns raw JSON records.
Each function returns None when the request fails so the caller can decide
whether to stop or fall back to seed data only.
"""

import requests

from analyst.config import API_BASE_URL, API_LIMITS, API_TIMEOUT_SECONDS


def fetch_data(endpoint: str, limit: int = 100) -> list | None:
    """
    Call one DummyJSON endpoint, e.g. '/products', and return the inner
    list of records. Returns None on any failure.
    """
    url = f"{API_BASE_URL}{endpoint}?limit={limit}"

    try:
        response = requests.get(url, timeout=API_TIMEOUT_SECONDS)
        response.raise_for_status()

        # The inner key matches the endpoint name, e.g. /products -> 'products'
        records = response.json().get(endpoint.strip("/"), [])

        print(f"SUCCESS: Fetched {len(records)} records from {url}")
        return records

    except requests.exceptions.ConnectionError:
        print(f"ERROR: Connection error, could not reach {url}")
    except requests.exceptions.Timeout:
        print(f"ERROR: Timeout, {url} took too long to respond")
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: HTTP error, {e}")
    except ValueError as e:
        print(f"ERROR: Response from {url} was not valid JSON, {e}")

    return None


def fetch_products(limit: int = API_LIMITS["products"]) -> list | None:
    """Fetch up to `limit` products."""
    return fetch_data("/products", limit)


def fetch_carts(limit: int = API_LIMITS["carts"]) -> list | None:
    """Fetch up to `limit` carts."""
    return fetch_data("/carts", limit)


def fetch_users(limit: int = API_LIMITS["users"]) -> list | None:
    """Fetch up to `limit` users."""
    return fetch_data("/users", limit)
