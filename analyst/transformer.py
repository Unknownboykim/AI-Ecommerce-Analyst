"""
transformer.py
--------------
Transform step. Turns raw API JSON into flat pandas DataFrames that match
the database tables.

Handles:
    flattening nested objects (dimensions, meta, address, company, bank)
    exploding child arrays into their own tables (reviews, cart items)
    dropping sensitive fields (password, ssn, card numbers, ip, and so on)
"""

import pandas as pd


def transform_products(raw: list) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Return (df_products, df_reviews).

    Flattened fields:
        dimensions.width/height/depth -> dim_width, dim_height, dim_depth
        meta.createdAt/updatedAt/barcode -> meta_createdAt, meta_updatedAt, meta_barcode
        tags[] -> one comma separated string
    """
    product_rows = []
    review_rows = []

    for p in raw:
        dims = p.get("dimensions") or {}
        meta = p.get("meta") or {}

        product_rows.append({
            "id":                   p.get("id"),
            "title":                p.get("title"),
            "description":          p.get("description"),
            "category":             p.get("category"),
            "price":                p.get("price"),
            "discountPercentage":   p.get("discountPercentage"),
            "rating":               p.get("rating"),
            "stock":                p.get("stock"),
            "brand":                p.get("brand"),
            "sku":                  p.get("sku"),
            "weight":               p.get("weight"),
            "availabilityStatus":   p.get("availabilityStatus"),
            "returnPolicy":         p.get("returnPolicy"),
            "warrantyInformation":  p.get("warrantyInformation"),
            "minimumOrderQuantity": p.get("minimumOrderQuantity"),
            "thumbnail":            p.get("thumbnail"),
            "tags":                 ", ".join(p.get("tags") or []),
            "dim_width":            dims.get("width"),
            "dim_height":           dims.get("height"),
            "dim_depth":            dims.get("depth"),
            "meta_createdAt":       meta.get("createdAt"),
            "meta_updatedAt":       meta.get("updatedAt"),
            "meta_barcode":         meta.get("barcode"),
        })

        # Each product carries its own reviews[] array; product_id is the foreign key
        for r in p.get("reviews") or []:
            review_rows.append({
                "product_id":     p.get("id"),
                "rating":         r.get("rating"),
                "comment":        r.get("comment"),
                "review_date":    r.get("date"),
                "reviewer_name":  r.get("reviewerName"),
                "reviewer_email": r.get("reviewerEmail"),
            })

    df_products = pd.DataFrame(product_rows)
    df_reviews = pd.DataFrame(review_rows)

    print(f"SUCCESS: Transformed products, {len(df_products)} rows, {len(df_reviews)} reviews")
    return df_products, df_reviews


def transform_carts(raw: list, known_product_ids: set | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Return (df_carts, df_cart_items).

    DummyJSON carts can reference products beyond the ones we fetched. When
    known_product_ids is given, line items for unknown products are dropped
    so they do not collide with the seeded product IDs (101 and up).
    """
    cart_rows = []
    item_rows = []

    for c in raw:
        cart_rows.append({
            "id":              c.get("id"),
            "userId":          c.get("userId"),
            "total":           c.get("total"),
            "discountedTotal": c.get("discountedTotal"),
            "totalProducts":   c.get("totalProducts"),
            "totalQuantity":   c.get("totalQuantity"),
        })

        for item in c.get("products") or []:
            if known_product_ids is not None and item.get("id") not in known_product_ids:
                continue
            item_rows.append({
                "cart_id":            c.get("id"),
                "product_id":         item.get("id"),
                "title":              item.get("title"),
                "price":              item.get("price"),
                "quantity":           item.get("quantity"),
                "total":              item.get("total"),
                "discountPercentage": item.get("discountPercentage"),
                "discountedTotal":    item.get("discountedTotal"),
                "thumbnail":          item.get("thumbnail"),
            })

    df_carts = pd.DataFrame(cart_rows)
    df_cart_items = pd.DataFrame(item_rows)

    print(f"SUCCESS: Transformed carts, {len(df_carts)} rows, {len(df_cart_items)} line items")
    return df_carts, df_cart_items


def transform_users(raw: list) -> pd.DataFrame:
    """
    Return one flat users DataFrame.

    Sensitive fields intentionally dropped:
        password, ssn, ein, ip, macAddress, userAgent, crypto, image,
        bank.cardNumber, bank.cardExpire
    """
    rows = []

    for u in raw:
        address = u.get("address") or {}
        hair = u.get("hair") or {}
        company = u.get("company") or {}
        bank = u.get("bank") or {}

        rows.append({
            "id":              u.get("id"),
            "firstName":       u.get("firstName"),
            "lastName":        u.get("lastName"),
            "maidenName":      u.get("maidenName"),
            "age":             u.get("age"),
            "gender":          u.get("gender"),
            "email":           u.get("email"),
            "phone":           u.get("phone"),
            "username":        u.get("username"),
            "birthDate":       u.get("birthDate"),
            "bloodGroup":      u.get("bloodGroup"),
            "height":          u.get("height"),
            "weight":          u.get("weight"),
            "eyeColor":        u.get("eyeColor"),
            "university":      u.get("university"),
            "role":            u.get("role"),
            "hair_color":      hair.get("color"),
            "hair_type":       hair.get("type"),
            "addr_street":     address.get("address"),
            "addr_city":       address.get("city"),
            "addr_state":      address.get("state"),
            "addr_postalCode": address.get("postalCode"),
            "addr_country":    address.get("country"),
            "company_name":    company.get("name"),
            "company_dept":    company.get("department"),
            "company_title":   company.get("title"),
            "bank_cardType":   bank.get("cardType"),
            "bank_currency":   bank.get("currency"),
            "bank_iban":       bank.get("iban"),
        })

    df_users = pd.DataFrame(rows)

    print(f"SUCCESS: Transformed users, {len(df_users)} rows")
    return df_users
