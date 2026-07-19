"""
database.py — Google Sheets database layer for the Grocery Price Tracker.
"""

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date
from typing import Optional

# ─── Default Categories ───────────────────────────────────────────────────────

CATEGORIES = [
    "Produce (Fruits & Veggies)",
    "Dairy & Eggs",
    "Meat & Seafood",
    "Snacks",
    "Household",
    "Personal Care",
    "Baby & Kids",
    "Pet Supplies",
    "Others",
]

# ─── Connection & Init ────────────────────────────────────────────────────────

def get_conn():
    return st.connection("gsheets", type=GSheetsConnection)

def _read_sheet(worksheet: str) -> pd.DataFrame:
    """Read a worksheet and ensure it exists and has headers."""
    try:
        df = get_conn().read(worksheet=worksheet, ttl=0)
        return df.fillna('')
    except Exception as e:
        # If the worksheet doesn't exist, return an empty DF with expected columns
        pass
    
    if worksheet == "Stores":
        return pd.DataFrame(columns=["id", "name"])
    elif worksheet == "Products":
        return pd.DataFrame(columns=["id", "store_id", "category", "item_name", "brand", "weight_volume", "unit"])
    elif worksheet == "Prices":
        return pd.DataFrame(columns=["id", "product_id", "date", "price"])
    return pd.DataFrame()

def _write_sheet(worksheet: str, df: pd.DataFrame):
    """Write dataframe back to the worksheet."""
    get_conn().update(worksheet=worksheet, data=df)
    # Clear the connection cache so the next read is fresh
    st.cache_data.clear()

def init_db():
    """Ensure tabs exist. For Google Sheets, we just test the connection."""
    pass

# ─── Store CRUD ───────────────────────────────────────────────────────────────

def get_stores() -> list[dict]:
    df = _read_sheet("Stores")
    if df.empty:
        return []
    # Sort by name
    df = df.sort_values(by="name")
    return df.to_dict('records')

def add_store(name: str) -> int:
    df = _read_sheet("Stores")
    new_id = 1 if df.empty else int(df["id"].max()) + 1
    new_row = {"id": new_id, "name": name.strip()}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    _write_sheet("Stores", df)
    return new_id


# ─── Product CRUD ─────────────────────────────────────────────────────────────

def get_categories() -> list[str]:
    return CATEGORIES

def get_brands(store_id: int) -> list[str]:
    df = _read_sheet("Products")
    if df.empty:
        return []
    store_products = df[df["store_id"] == store_id]
    brands = store_products["brand"].replace('', pd.NA).dropna().unique().tolist()
    return sorted([b for b in brands if str(b).strip() != ""])

def add_product(
    store_id: int,
    category: str,
    item_name: str,
    brand: str = "",
    weight_volume: str = "",
    unit: str = "",
) -> int:
    df = _read_sheet("Products")
    new_id = 1 if df.empty else int(df["id"].max()) + 1
    new_row = {
        "id": new_id,
        "store_id": store_id,
        "category": category,
        "item_name": item_name.strip(),
        "brand": brand.strip(),
        "weight_volume": weight_volume.strip(),
        "unit": unit.strip()
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    _write_sheet("Products", df)
    return new_id


def get_products(store_id: Optional[int] = None) -> list[dict]:
    products_df = _read_sheet("Products")
    prices_df = _read_sheet("Prices")
    
    if products_df.empty:
        return []
        
    if store_id is not None:
        products_df = products_df[products_df["store_id"] == store_id]
        
    products = products_df.to_dict('records')
    
    # Attach latest price
    for p in products:
        p_id = p["id"]
        product_prices = prices_df[prices_df["product_id"] == p_id]
        if not product_prices.empty:
            # Sort by date descending and get the first price
            latest = product_prices.sort_values(by="date", ascending=False).iloc[0]
            p["latest_price"] = float(latest["price"])
        else:
            p["latest_price"] = 0.0
            
    # Sort products alphabetically
    products = sorted(products, key=lambda x: str(x.get("item_name", "")).lower())
    return products

def get_product_by_id(product_id: int) -> Optional[dict]:
    products_df = _read_sheet("Products")
    if products_df.empty:
        return None
        
    product = products_df[products_df["id"] == product_id]
    if product.empty:
        return None
        
    p = product.iloc[0].to_dict()
    
    prices_df = _read_sheet("Prices")
    product_prices = prices_df[prices_df["product_id"] == product_id]
    if not product_prices.empty:
        latest = product_prices.sort_values(by="date", ascending=False).iloc[0]
        p["latest_price"] = float(latest["price"])
    else:
        p["latest_price"] = 0.0
        
    return p

def delete_product(product_id: int):
    # Delete from products
    products_df = _read_sheet("Products")
    products_df = products_df[products_df["id"] != product_id]
    _write_sheet("Products", products_df)
    
    # Delete from prices
    prices_df = _read_sheet("Prices")
    prices_df = prices_df[prices_df["product_id"] != product_id]
    _write_sheet("Prices", prices_df)


# ─── Price History CRUD ───────────────────────────────────────────────────────

def add_price(product_id: int, price: float, entry_date: str = None):
    if entry_date is None:
        entry_date = date.today().isoformat()
        
    df = _read_sheet("Prices")
    new_id = 1 if df.empty else int(df["id"].max()) + 1
    new_row = {
        "id": new_id,
        "product_id": product_id,
        "date": entry_date,
        "price": float(price)
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    _write_sheet("Prices", df)


def update_price_today(product_id: int, price: float):
    """
    If a price for today already exists, update it.
    Otherwise, insert a new record for today.
    """
    today_str = date.today().isoformat()
    df = _read_sheet("Prices")
    
    if not df.empty:
        mask = (df["product_id"] == product_id) & (df["date"] == today_str)
        if mask.any():
            # Update existing
            df.loc[mask, "price"] = float(price)
            _write_sheet("Prices", df)
            return
            
    # If we reach here, no record for today exists. Insert new.
    add_price(product_id, price, today_str)


def get_price_history(product_id: int) -> list[dict]:
    df = _read_sheet("Prices")
    if df.empty:
        return []
        
    product_prices = df[df["product_id"] == product_id]
    product_prices = product_prices.sort_values(by="date")
    return product_prices.to_dict('records')
