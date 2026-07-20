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
        # Use ttl="10m" to cache reads for 10 minutes (prevents API rate limits).
        # Writes will automatically clear this cache.
        df = get_conn().read(worksheet=worksheet, ttl="10m")
        df = df.fillna('')
    except Exception as e:
        if "WorksheetNotFound" not in str(type(e)):
            raise e
        df = pd.DataFrame()
    
    # Ensure expected columns exist
    if worksheet == "Stores":
        expected_cols = ["id", "name"]
    elif worksheet == "Products":
        expected_cols = ["id", "category", "item_name", "brand", "weight_volume", "unit"]
    elif worksheet == "Prices":
        expected_cols = ["id", "product_id", "store_id", "date", "price"]
    else:
        expected_cols = []
        
    for col in expected_cols:
        if col not in df.columns:
            df[col] = pd.Series(dtype=object)
            
    return df

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
    new_id = 1 if df.empty or pd.isna(pd.to_numeric(df["id"], errors="coerce").max()) else int(pd.to_numeric(df["id"], errors="coerce").max()) + 1
    new_row = {"id": new_id, "name": name.strip()}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    _write_sheet("Stores", df)
    return new_id


# ─── Product CRUD ─────────────────────────────────────────────────────────────

def get_categories() -> list[str]:
    return CATEGORIES

def get_brands() -> list[str]:
    df = _read_sheet("Products")
    if df.empty:
        return []
    brands = df["brand"].replace('', pd.NA).dropna().unique().tolist()
    return sorted([b for b in brands if str(b).strip() != ""])

def add_product(
    category: str,
    item_name: str,
    brand: str = "",
    weight_volume: str = "",
    unit: str = "",
) -> int:
    df = _read_sheet("Products")
    
    # Check if a product with the exact same name/brand/weight already exists globally to avoid duplicates
    if not df.empty:
        mask = (df["item_name"].astype(str).str.lower() == item_name.strip().lower()) & \
               (df["brand"].astype(str).str.lower() == brand.strip().lower()) & \
               (df["weight_volume"].astype(str).str.lower() == weight_volume.strip().lower()) & \
               (df["unit"].astype(str).str.lower() == unit.strip().lower())
        existing = df[mask]
        if not existing.empty:
            return int(existing.iloc[0]["id"])
        
    new_id = 1 if df.empty or pd.isna(pd.to_numeric(df["id"], errors="coerce").max()) else int(pd.to_numeric(df["id"], errors="coerce").max()) + 1
    new_row = {
        "id": new_id,
        "category": category,
        "item_name": item_name.strip(),
        "brand": brand.strip(),
        "weight_volume": weight_volume.strip(),
        "unit": unit.strip()
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    _write_sheet("Products", df)
    return new_id


def get_products(store_id: Optional[int] = None, category: str = None, brand: str = None, search: str = None) -> list[dict]:
    products_df = _read_sheet("Products")
    prices_df = _read_sheet("Prices")
    
    if products_df.empty:
        return []
        
    if category:
        products_df = products_df[products_df["category"] == category]
    if brand:
        products_df = products_df[products_df["brand"] == brand]
    if search:
        search = search.lower()
        products_df = products_df[products_df["item_name"].str.lower().str.contains(search) | products_df["brand"].str.lower().str.contains(search)]
        
    products = products_df.to_dict('records')
    
    # Attach latest price for the requested store (or globally if store_id is None)
    for p in products:
        p_id = p["id"]
        product_prices = prices_df[prices_df["product_id"] == p_id]
        
        if store_id is not None:
            product_prices = product_prices[product_prices["store_id"] == store_id]
            
        if not product_prices.empty:
            # Sort by date descending and get the first price
            latest = product_prices.sort_values(by="date", ascending=False).iloc[0]
            p["latest_price"] = float(latest["price"])
        else:
            p["latest_price"] = None # Change to None to distinguish "No price logged at this store" from "0.0"
            
    # Sort products alphabetically
    products = sorted(products, key=lambda x: str(x.get("item_name", "")).lower())
    return products

def get_product_by_id(product_id: int, store_id: Optional[int] = None) -> Optional[dict]:
    products_df = _read_sheet("Products")
    if products_df.empty:
        return None
        
    product = products_df[products_df["id"] == product_id]
    if product.empty:
        return None
        
    p = product.iloc[0].to_dict()
    
    prices_df = _read_sheet("Prices")
    product_prices = prices_df[prices_df["product_id"] == product_id]
    
    if store_id is not None:
        product_prices = product_prices[product_prices["store_id"] == store_id]
        
    if not product_prices.empty:
        latest = product_prices.sort_values(by="date", ascending=False).iloc[0]
        p["latest_price"] = float(latest["price"])
    else:
        p["latest_price"] = None
        
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

def add_price(product_id: int, store_id: int, price: float, entry_date: str = None):
    if entry_date is None:
        entry_date = date.today().isoformat()
        
    df = _read_sheet("Prices")
    new_id = 1 if df.empty or pd.isna(pd.to_numeric(df["id"], errors="coerce").max()) else int(pd.to_numeric(df["id"], errors="coerce").max()) + 1
    new_row = {
        "id": new_id,
        "product_id": product_id,
        "store_id": store_id,
        "date": entry_date,
        "price": float(price)
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    _write_sheet("Prices", df)


def update_price_today(product_id: int, store_id: int, price: float):
    """
    If a price for today already exists at this store, update it.
    Otherwise, insert a new record for today.
    """
    today_str = date.today().isoformat()
    df = _read_sheet("Prices")
    
    if not df.empty:
        mask = (df["product_id"] == product_id) & (df["store_id"] == store_id) & (df["date"] == today_str)
        if mask.any():
            # Update existing
            df.loc[mask, "price"] = float(price)
            _write_sheet("Prices", df)
            return
            
    # If we reach here, no record for today exists. Insert new.
    add_price(product_id, store_id, price, today_str)


def get_price_history(product_id: int, store_id: Optional[int] = None) -> list[dict]:
    df = _read_sheet("Prices")
    if df.empty:
        return []
        
    product_prices = df[df["product_id"] == product_id]
    if store_id is not None:
        product_prices = product_prices[product_prices["store_id"] == store_id]
        
    product_prices = product_prices.sort_values(by="date")
    return product_prices.to_dict('records')

def get_all_prices_joined() -> list[dict]:
    prices_df = _read_sheet("Prices")
    if prices_df.empty:
        return []
        
    products_df = _read_sheet("Products")
    stores_df = _read_sheet("Stores")
    
    df = prices_df.merge(products_df, left_on="product_id", right_on="id", suffixes=("_price", "_prod"), how="left")
    df = df.merge(stores_df, left_on="store_id", right_on="id", suffixes=("", "_store"), how="left")
    
    result = []
    for _, row in df.iterrows():
        result.append({
            "price_id": row.get("id_price"),
            "product_id": row.get("product_id"),
            "Delete": False,
            "Store": str(row.get("name", "")),
            "Category": str(row.get("category", "")),
            "Item": str(row.get("item_name", "")),
            "Brand": str(row.get("brand", "")),
            "Weight": str(row.get("weight_volume", "")),
            "Unit": str(row.get("unit", "")),
            "Price": float(row.get("price", 0.0)),
            "Date": str(row.get("date", ""))
        })
    return result
