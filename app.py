"""
app.py — Grocery Price Tracker
A Streamlit application to track grocery prices across stores using OCR receipts or manual entry.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime
from PIL import Image

import database as db
from ocr_engine import check_tesseract, extract_text, preprocess_image, detect_prices_from_text

# ─── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Grocery Price Tracker",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* ── Import Google Font ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* ── Global ── */
    *, .stApp, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif !important;
    }

    .stApp {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%) !important;
        border-right: 1px solid rgba(56, 189, 248, 0.1);
    }

    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #e2e8f0 !important;
    }

    /* ── Headers ── */
    h1, h2, h3 {
        color: #f1f5f9 !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }

    /* ── Metric cards ── */
    [data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(56, 189, 248, 0.15);
        border-radius: 16px;
        padding: 20px 24px;
        backdrop-filter: blur(12px);
        transition: all 0.3s ease;
    }

    [data-testid="stMetric"]:hover {
        border-color: rgba(56, 189, 248, 0.4);
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(56, 189, 248, 0.1);
    }

    [data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    [data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        font-size: 2rem !important;
        font-weight: 800 !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(15, 23, 42, 0.6);
        border-radius: 16px;
        padding: 6px;
        border: 1px solid rgba(56, 189, 248, 0.1);
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 12px;
        padding: 12px 24px;
        color: #94a3b8;
        font-weight: 600;
        font-size: 0.9rem;
        transition: all 0.3s ease;
        background: transparent;
        border: none;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%) !important;
        color: #ffffff !important;
        box-shadow: 0 4px 16px rgba(14, 165, 233, 0.3);
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: #e2e8f0;
    }

    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 24px;
    }

    /* ── Buttons ── */
    .stButton > button {
        background: linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        transition: all 0.3s ease !important;
        letter-spacing: 0.02em;
    }

    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(14, 165, 233, 0.35) !important;
    }

    .stButton > button:active {
        transform: translateY(0) !important;
    }

    /* ── Form inputs ── */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div,
    .stMultiSelect > div > div,
    .stTextArea > div > div > textarea {
        background: rgba(30, 41, 59, 0.8) !important;
        border: 1px solid rgba(56, 189, 248, 0.2) !important;
        border-radius: 12px !important;
        color: #e2e8f0 !important;
        transition: border-color 0.3s ease;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #0ea5e9 !important;
        box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.15) !important;
    }

    /* ── Data editor / tables ── */
    [data-testid="stDataFrame"],
    .stDataFrame {
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid rgba(56, 189, 248, 0.1);
    }

    /* ── File uploader ── */
    [data-testid="stFileUploader"] {
        background: rgba(30, 41, 59, 0.5);
        border: 2px dashed rgba(56, 189, 248, 0.3);
        border-radius: 16px;
        padding: 24px;
        transition: all 0.3s ease;
    }

    [data-testid="stFileUploader"]:hover {
        border-color: rgba(56, 189, 248, 0.6);
        background: rgba(30, 41, 59, 0.7);
    }

    /* ── Expander ── */
    .streamlit-expanderHeader {
        background: rgba(30, 41, 59, 0.6) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(56, 189, 248, 0.1) !important;
        color: #e2e8f0 !important;
        font-weight: 600 !important;
    }

    /* ── Success/Info/Warning boxes ── */
    .stAlert {
        border-radius: 12px !important;
        border: none !important;
    }

    /* ── Divider ── */
    hr {
        border-color: rgba(56, 189, 248, 0.1) !important;
    }

    /* ── Hero title ── */
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -0.03em;
        line-height: 1.2;
        margin-bottom: 4px;
    }

    .hero-subtitle {
        color: #64748b;
        font-size: 1rem;
        font-weight: 400;
        margin-top: 0;
    }

    /* ── Category badge ── */
    .category-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* ── Card container ── */
    .glass-card {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(56, 189, 248, 0.12);
        border-radius: 16px;
        padding: 24px;
        backdrop-filter: blur(12px);
        margin-bottom: 16px;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: rgba(15, 23, 42, 0.4);
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(56, 189, 248, 0.3);
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(56, 189, 248, 0.5);
    }
</style>
""", unsafe_allow_html=True)

# ─── Initialize database ─────────────────────────────────────────────────────

db.init_db()

# ─── Session state defaults ──────────────────────────────────────────────────

if "selected_store_id" not in st.session_state:
    st.session_state.selected_store_id = None
if "ocr_text" not in st.session_state:
    st.session_state.ocr_text = ""
if "ocr_items" not in st.session_state:
    st.session_state.ocr_items = []

# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown('<div class="hero-title">🛒 Grocery Tracker</div>', unsafe_allow_html=True)
    st.markdown('<p class="hero-subtitle">Track prices across stores</p>', unsafe_allow_html=True)
    st.markdown("---")

    # ── Store selector ──
    st.markdown("### 🏪 Select Store")
    stores = db.get_stores()
    store_names = [s["name"] for s in stores]
    store_map = {s["name"]: s["id"] for s in stores}

    selected_store_name = None

    if stores:
        selected_store_name = st.selectbox(
            "Grocery Store",
            options=store_names,
            key="store_selector",
            label_visibility="collapsed",
        )
        selected_store_id = store_map[selected_store_name]
        st.session_state.selected_store_id = selected_store_id
    else:
        selected_store_id = None

    # ── Add new store ──
    # Show prominently when no stores exist, otherwise in expander
    def _add_store_form():
        new_store_name = st.text_input("Store Name", key="new_store_input", placeholder="e.g. SM Supermarket, Puregold...")
        if st.button("Add Store", key="add_store_btn", use_container_width=True):
            if new_store_name.strip():
                try:
                    db.add_store(new_store_name)
                    st.success(f"✅ Added **{new_store_name}**")
                    st.rerun()
                except Exception as e:
                    st.error(f"Store already exists or error: {e}")
            else:
                st.warning("Enter a store name")

    if not stores:
        st.info("👋 **Welcome!** Add your first grocery store to get started.")
        _add_store_form()
    else:
        with st.expander("➕ Add New Store"):
            _add_store_form()

    st.markdown("---")

    # ── Filters ──
    if selected_store_id:
        st.markdown("### 🔍 Filters")

        # Category filter
        available_categories = db.get_categories(selected_store_id)
        if available_categories:
            filter_category = st.selectbox(
                "Category",
                options=["All Categories"] + available_categories,
                key="filter_category",
            )
        else:
            filter_category = "All Categories"
            st.caption("No categories yet — add products first")

        # Brand filter
        cat_for_brand = filter_category if filter_category != "All Categories" else None
        available_brands = db.get_brands(selected_store_id, cat_for_brand)
        if available_brands:
            filter_brand = st.selectbox(
                "Brand",
                options=["All Brands"] + available_brands,
                key="filter_brand",
            )
        else:
            filter_brand = "All Brands"
            st.caption("No brands yet")

        # Search
        search_query = st.text_input("🔎 Search items", key="search_items", placeholder="Type to search...")

        st.markdown("---")

        # ── Stats ──
        product_count = db.get_product_count_by_store(selected_store_id)
        st.metric("Products Tracked", product_count)
        st.caption(f"📅 Today: {date.today().strftime('%B %d, %Y')}")


# ─── Main Content ────────────────────────────────────────────────────────────

st.markdown('<div class="hero-title">🛒 Grocery Price Tracker</div>', unsafe_allow_html=True)
st.markdown(f'<p class="hero-subtitle">Currently viewing: <strong>{selected_store_name if selected_store_id else "No store selected"}</strong> &nbsp;•&nbsp; {date.today().strftime("%A, %B %d, %Y")}</p>', unsafe_allow_html=True)
st.markdown("")

# ── Tabs ──
tab_dashboard, tab_ocr, tab_manual = st.tabs([
    "📋 Price Dashboard",
    "📸 Scan Price Label",
    "✏️ Manual Entry",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: PRICE DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

with tab_dashboard:
    if not selected_store_id:
        st.info("👈 Select a store from the sidebar to get started.")
    else:
        # Fetch products with filters
        cat_filter = filter_category if filter_category != "All Categories" else None
        brand_filter = filter_brand if filter_brand != "All Brands" else None
        search_val = search_query.strip() if search_query else None

        products = db.get_products(
            store_id=selected_store_id,
            category=cat_filter,
            brand=brand_filter,
            search=search_val,
        )

        if not products:
            st.markdown("""
            <div class="glass-card" style="text-align: center; padding: 60px 24px;">
                <div style="font-size: 4rem; margin-bottom: 16px;">📦</div>
                <h3 style="color: #94a3b8; margin-bottom: 8px;">No products yet</h3>
                <p style="color: #64748b;">Add products using the <strong>Manual Entry</strong> tab or <strong>Scan a Price Label</strong> to get started.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            # ── Summary metrics ──
            col1, col2, col3, col4 = st.columns(4)
            prices = [p["latest_price"] for p in products if p["latest_price"] is not None]

            with col1:
                st.metric("Total Items", len(products))
            with col2:
                st.metric("Avg Price", f"₱{sum(prices)/len(prices):.2f}" if prices else "—")
            with col3:
                st.metric("Highest", f"₱{max(prices):.2f}" if prices else "—")
            with col4:
                st.metric("Lowest", f"₱{min(prices):.2f}" if prices else "—")

            st.markdown("")

            # ── Products table ──
            df = pd.DataFrame(products)

            # Format for display
            display_df = df[["category", "item_name", "brand", "weight_volume", "unit", "latest_price", "last_updated"]].copy()
            display_df.columns = ["Category", "Item", "Brand", "Weight/Volume", "Unit", "Price (₱)", "Last Updated"]
            display_df["Price (₱)"] = display_df["Price (₱)"].apply(lambda x: f"₱{x:.2f}" if pd.notna(x) else "—")
            display_df["Last Updated"] = display_df["Last Updated"].apply(lambda x: x if x else "—")

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                height=min(400, len(display_df) * 40 + 60),
                column_config={
                    "Category": st.column_config.TextColumn("Category", width="medium"),
                    "Item": st.column_config.TextColumn("Item", width="large"),
                    "Brand": st.column_config.TextColumn("Brand", width="medium"),
                    "Price (₱)": st.column_config.TextColumn("Price (₱)", width="small"),
                },
            )

            st.markdown("---")

            # ── Quick Price Update ──
            st.markdown("### ⚡ Quick Price Update")
            st.caption("Select a product to update its price for today.")

            product_options = {
                f"{p['item_name']} — {p['brand']} ({p['weight_volume']} {p['unit']})".strip(): p["id"]
                for p in products
            }

            col_select, col_price, col_btn = st.columns([3, 1.5, 1])

            with col_select:
                selected_product_label = st.selectbox(
                    "Product",
                    options=list(product_options.keys()),
                    key="quick_update_product",
                    label_visibility="collapsed",
                    placeholder="Select a product to update...",
                )

            with col_price:
                new_price = st.number_input(
                    "New Price",
                    min_value=0.0,
                    step=0.25,
                    format="%.2f",
                    key="quick_update_price",
                    label_visibility="collapsed",
                    placeholder="Price",
                )

            with col_btn:
                if st.button("Update ₱", key="quick_update_btn", use_container_width=True):
                    if selected_product_label and new_price > 0:
                        product_id = product_options[selected_product_label]
                        db.update_price_today(product_id, new_price)
                        st.success(f"✅ Updated to ₱{new_price:.2f}")
                        st.rerun()
                    else:
                        st.warning("Select a product and enter a price")

            st.markdown("---")

            # ── Price History Chart ──
            st.markdown("### 📈 Price History")

            chart_product_label = st.selectbox(
                "Select product to view price history",
                options=list(product_options.keys()),
                key="chart_product",
            )

            if chart_product_label:
                chart_product_id = product_options[chart_product_label]
                history = db.get_price_history(chart_product_id)

                if history and len(history) > 0:
                    hist_df = pd.DataFrame(history)
                    hist_df["date_recorded"] = pd.to_datetime(hist_df["date_recorded"])

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=hist_df["date_recorded"],
                        y=hist_df["price"],
                        mode="lines+markers",
                        name="Price",
                        line=dict(color="#38bdf8", width=3, shape="spline"),
                        marker=dict(size=8, color="#6366f1", line=dict(width=2, color="#38bdf8")),
                        fill="tozeroy",
                        fillcolor="rgba(56, 189, 248, 0.08)",
                    ))

                    fig.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        xaxis=dict(
                            title="Date",
                            gridcolor="rgba(56, 189, 248, 0.1)",
                            showline=True,
                            linecolor="rgba(56, 189, 248, 0.2)",
                        ),
                        yaxis=dict(
                            title="Price (₱)",
                            gridcolor="rgba(56, 189, 248, 0.1)",
                            showline=True,
                            linecolor="rgba(56, 189, 248, 0.2)",
                            tickprefix="₱",
                        ),
                        margin=dict(l=0, r=0, t=20, b=0),
                        height=350,
                        hovermode="x unified",
                    )

                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No price history yet for this product. Update the price to start tracking.")

            # ── Delete product ──
            with st.expander("🗑️ Delete a Product"):
                del_product_label = st.selectbox(
                    "Select product to delete",
                    options=list(product_options.keys()),
                    key="delete_product",
                )
                if st.button("🗑️ Delete Product", key="delete_btn", type="secondary"):
                    if del_product_label:
                        del_id = product_options[del_product_label]
                        db.delete_product(del_id)
                        st.success("Product deleted.")
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: SCAN PRICE LABEL (OCR)
# ═══════════════════════════════════════════════════════════════════════════════

with tab_ocr:
    st.markdown("### 📸 Scan Price Label")
    st.caption("Snap or upload a photo of a shelf price tag. OCR will extract the text so you can quickly fill in the product details.")

    if not selected_store_id:
        st.info("👈 Select a store from the sidebar first before scanning.")
    else:
        # Check Tesseract availability
        tesseract_ok, tesseract_msg = check_tesseract()

        if not tesseract_ok:
            st.markdown(f"""
            <div class="glass-card">
                {tesseract_msg}
            </div>
            """, unsafe_allow_html=True)
            st.markdown("""
            <div class="glass-card">
                <h4 style="color: #f1f5f9;">📋 Installation Steps (Windows)</h4>
                <ol style="color: #94a3b8;">
                    <li>Download Tesseract from <a href="https://github.com/UB-Mannheim/tesseract/wiki" target="_blank">UB-Mannheim GitHub</a></li>
                    <li>Run the installer (default path: <code>C:\\Program Files\\Tesseract-OCR</code>)</li>
                    <li>Add to PATH or set in Python: <code>pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'</code></li>
                    <li>Restart this Streamlit app</li>
                </ol>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.success(tesseract_msg)

        st.markdown("")

        # ── Image source: camera or file upload ──
        input_method = st.radio(
            "How do you want to capture the price label?",
            options=["📷 Take Photo (Camera)", "📁 Upload Image File"],
            horizontal=True,
            key="ocr_input_method",
            label_visibility="collapsed",
        )

        image = None

        if input_method == "📷 Take Photo (Camera)":
            camera_image = st.camera_input(
                "Point your camera at the price label and snap",
                key="camera_capture",
            )
            if camera_image is not None:
                image = Image.open(camera_image)
        else:
            uploaded_file = st.file_uploader(
                "Upload price label photo",
                type=["jpg", "jpeg", "png", "bmp", "webp"],
                key="label_upload",
                help="Upload a photo of a grocery shelf price tag",
            )
            if uploaded_file is not None:
                image = Image.open(uploaded_file)

        # ── Process the image automatically ──
        if image is not None:
            # Auto-run OCR immediately
            with st.spinner("🔍 Reading price label..."):
                processed_image, _ = preprocess_image(image)
                extracted = extract_text(image)
                detected_prices = detect_prices_from_text(extracted)

            # ── Show image + instant price confirmation ──
            col_img, col_result = st.columns([1, 1.5])

            with col_img:
                st.markdown("**📷 Captured Label**")
                st.image(image, use_container_width=True)

            with col_result:
                # Big price confirmation banner
                if detected_prices:
                    primary_price = detected_prices[0]
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, rgba(34, 197, 94, 0.15) 0%, rgba(16, 185, 129, 0.1) 100%);
                        border: 2px solid rgba(34, 197, 94, 0.4);
                        border-radius: 20px;
                        padding: 28px;
                        text-align: center;
                        margin-bottom: 12px;
                    ">
                        <div style="color: #86efac; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 8px;">💰 Detected Price</div>
                        <div style="color: #22c55e; font-size: 3.2rem; font-weight: 800; line-height: 1;">₱{primary_price:,.2f}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    if len(detected_prices) > 1:
                        other_prices = ", ".join([f"₱{p:,.2f}" for p in detected_prices[1:]])
                        st.caption(f"Other numbers found: {other_prices}")
                else:
                    st.markdown("""
                    <div style="
                        background: rgba(234, 179, 8, 0.1);
                        border: 2px solid rgba(234, 179, 8, 0.3);
                        border-radius: 20px;
                        padding: 28px;
                        text-align: center;
                        margin-bottom: 12px;
                    ">
                        <div style="color: #fbbf24; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 8px;">⚠️ No Price Detected</div>
                        <div style="color: #fbbf24; font-size: 1.1rem;">Enter the price manually below</div>
                    </div>
                    """, unsafe_allow_html=True)

                # Show raw OCR text in an expander
                with st.expander("📝 Raw OCR Text", expanded=False):
                    st.code(extracted, language=None)

            st.markdown("---")

            # ── Product entry form ──
            st.markdown("### 🏷️ Enter Product Details")
            st.caption(f"Saving to: **{selected_store_name}** • Date: **{date.today().strftime('%B %d, %Y')}**")

            # ── Product form pre-filled from OCR context ──
            with st.form("ocr_product_form", clear_on_submit=True):
                col1, col2 = st.columns(2)

                with col1:
                    ocr_category = st.selectbox(
                        "Category *",
                        options=db.DEFAULT_CATEGORIES,
                        key="ocr_form_category",
                    )

                with col2:
                    ocr_item_name = st.text_input(
                        "Item Name *",
                        key="ocr_form_item",
                        placeholder="e.g. Corned Beef, Cooking Oil",
                    )

                col3, col4 = st.columns(2)

                with col3:
                    existing_brands = db.get_brands(selected_store_id)
                    brand_options = ["(Type new brand)"] + existing_brands
                    ocr_brand_select = st.selectbox(
                        "Brand",
                        options=brand_options,
                        key="ocr_form_brand_select",
                    )

                with col4:
                    ocr_brand_custom = st.text_input(
                        "Brand Name",
                        key="ocr_form_brand_custom",
                        placeholder="e.g. Argentina, Lucky Me",
                    )

                ocr_final_brand = (
                    ocr_brand_custom if ocr_brand_select == "(Type new brand)"
                    else ocr_brand_select
                )

                col5, col6, col7 = st.columns([2, 1, 2])

                with col5:
                    ocr_weight = st.text_input(
                        "Weight / Volume",
                        key="ocr_form_weight",
                        placeholder="e.g. 250, 1.5, 500",
                    )

                with col6:
                    ocr_unit = st.selectbox(
                        "Unit",
                        options=["g", "kg", "mL", "L", "pcs", "pack", "box", "can", "bottle", "sachet", "oz", "lb"],
                        key="ocr_form_unit",
                    )

                with col7:
                    # Pre-fill with detected price
                    default_price = detected_prices[0] if detected_prices else 0.0
                    ocr_price = st.number_input(
                        "Price (₱) *",
                        min_value=0.0,
                        value=default_price,
                        step=0.25,
                        format="%.2f",
                        key="ocr_form_price",
                    )

                st.markdown("")
                ocr_submitted = st.form_submit_button(
                    "💾 Save Product from Label",
                    use_container_width=True,
                )

                if ocr_submitted:
                    if not ocr_item_name.strip():
                        st.error("❌ Item name is required.")
                    elif ocr_price <= 0:
                        st.error("❌ Price must be greater than 0.")
                    else:
                        product_id = db.add_product(
                            store_id=selected_store_id,
                            category=ocr_category,
                            item_name=ocr_item_name,
                            brand=ocr_final_brand,
                            weight_volume=ocr_weight,
                            unit=ocr_unit,
                        )
                        db.add_price(product_id, ocr_price)
                        st.success(
                            f"✅ Saved **{ocr_item_name}** ({ocr_final_brand}) at **₱{ocr_price:.2f}**"
                        )
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: MANUAL ENTRY
# ═══════════════════════════════════════════════════════════════════════════════

with tab_manual:
    st.markdown("### ✏️ Add or Update Product")
    st.caption(f"Adding to: **{selected_store_name if selected_store_id else 'No store selected'}** &nbsp;•&nbsp; Date: **{date.today().strftime('%B %d, %Y')}**")

    if not selected_store_id:
        st.info("👈 Select a store from the sidebar first.")
    else:
        st.markdown("")

        # ── Mode toggle: New product vs Update existing ──
        entry_mode = st.radio(
            "Mode",
            options=["🆕 Add New Product", "🔄 Update Existing Product Price"],
            horizontal=True,
            key="entry_mode",
            label_visibility="collapsed",
        )

        st.markdown("")

        if entry_mode == "🆕 Add New Product":
            # ── New product form ──
            with st.form("new_product_form", clear_on_submit=True):
                st.markdown("#### Product Details")

                col1, col2 = st.columns(2)

                with col1:
                    # Category: selectbox + option for custom
                    all_categories = db.DEFAULT_CATEGORIES
                    category_option = st.selectbox(
                        "Category *",
                        options=all_categories + ["➕ Custom Category"],
                        key="manual_category",
                    )

                with col2:
                    custom_category = ""
                    if category_option == "➕ Custom Category":
                        custom_category = st.text_input(
                            "Custom Category Name *",
                            key="manual_custom_cat",
                            placeholder="e.g. Organic Products",
                        )
                    else:
                        st.markdown("")  # Spacer

                final_category = custom_category if category_option == "➕ Custom Category" else category_option

                item_name = st.text_input(
                    "Item Name *",
                    key="manual_item_name",
                    placeholder="e.g. Corned Beef, Instant Noodles, Cooking Oil",
                )

                col3, col4 = st.columns(2)

                with col3:
                    # Brand: selectbox with existing + custom
                    existing_brands = db.get_brands(selected_store_id)
                    brand_options = ["(No brand / Generic)"] + existing_brands + ["➕ New Brand"]
                    brand_option = st.selectbox(
                        "Brand",
                        options=brand_options,
                        key="manual_brand",
                    )

                with col4:
                    custom_brand = ""
                    if brand_option == "➕ New Brand":
                        custom_brand = st.text_input(
                            "Brand Name",
                            key="manual_custom_brand",
                            placeholder="e.g. Argentina, Lucky Me",
                        )
                    else:
                        st.markdown("")

                final_brand = (
                    custom_brand if brand_option == "➕ New Brand"
                    else "" if brand_option == "(No brand / Generic)"
                    else brand_option
                )

                col5, col6, col7 = st.columns([2, 1, 2])

                with col5:
                    weight_volume = st.text_input(
                        "Weight / Volume",
                        key="manual_weight",
                        placeholder="e.g. 250, 1, 500",
                    )

                with col6:
                    unit = st.selectbox(
                        "Unit",
                        options=["g", "kg", "mL", "L", "pcs", "pack", "box", "can", "bottle", "sachet", "oz", "lb"],
                        key="manual_unit",
                    )

                with col7:
                    price = st.number_input(
                        "Price (₱) *",
                        min_value=0.0,
                        step=0.25,
                        format="%.2f",
                        key="manual_price",
                    )

                st.markdown("")
                submitted = st.form_submit_button(
                    "💾 Save Product",
                    use_container_width=True,
                )

                if submitted:
                    if not item_name.strip():
                        st.error("❌ Item name is required.")
                    elif not final_category.strip():
                        st.error("❌ Category is required.")
                    elif price <= 0:
                        st.error("❌ Price must be greater than 0.")
                    else:
                        product_id = db.add_product(
                            store_id=selected_store_id,
                            category=final_category,
                            item_name=item_name,
                            brand=final_brand,
                            weight_volume=weight_volume,
                            unit=unit,
                        )
                        db.add_price(product_id, price)
                        st.success(
                            f"✅ Saved **{item_name}** ({final_brand}) at **₱{price:.2f}** "
                            f"to {selected_store_name}"
                        )
                        st.rerun()

        else:
            # ── Update existing product price ──
            st.markdown("#### Select Product to Update")

            existing_products = db.get_products(store_id=selected_store_id)

            if not existing_products:
                st.info("No products in this store yet. Add some first using **Add New Product**.")
            else:
                product_options_update = {
                    f"{p['item_name']} — {p['brand']} ({p['weight_volume']} {p['unit']}) | Current: ₱{p['latest_price']:.2f if p['latest_price'] else 0:.2f}".strip(): p["id"]
                    for p in existing_products
                }

                selected_update = st.selectbox(
                    "Product",
                    options=list(product_options_update.keys()),
                    key="update_select",
                    placeholder="Search and select a product...",
                )

                if selected_update:
                    product_id = product_options_update[selected_update]
                    product_info = db.get_product_by_id(product_id)

                    if product_info:
                        st.markdown(f"""
                        <div class="glass-card">
                            <strong style="color: #38bdf8;">{product_info['item_name']}</strong>
                            <span style="color: #64748b;"> — {product_info['brand']}</span><br>
                            <span style="color: #94a3b8;">📦 {product_info['weight_volume']} {product_info['unit']} &nbsp;•&nbsp;
                            📁 {product_info['category']}</span><br>
                            <span style="color: #94a3b8;">💰 Last price:
                            <strong style="color: #22c55e;">₱{product_info['latest_price']:.2f if product_info['latest_price'] else 0:.2f}</strong>
                            &nbsp;•&nbsp; Updated: {product_info['last_updated'] or 'Never'}</span>
                        </div>
                        """, unsafe_allow_html=True)

                    col_up_price, col_up_btn = st.columns([2, 1])
                    with col_up_price:
                        update_price = st.number_input(
                            "New Price (₱)",
                            min_value=0.0,
                            step=0.25,
                            format="%.2f",
                            key="update_price_input",
                            value=product_info["latest_price"] if product_info and product_info["latest_price"] else 0.0,
                        )
                    with col_up_btn:
                        st.markdown("")  # Align button
                        if st.button("💾 Update Price", key="update_price_btn", use_container_width=True):
                            if update_price > 0:
                                db.update_price_today(product_id, update_price)
                                st.success(f"✅ Price updated to **₱{update_price:.2f}** for today ({date.today().strftime('%B %d, %Y')})")
                                st.rerun()
                            else:
                                st.warning("Enter a price greater than 0")

                    # Show price history
                    history = db.get_price_history(product_id)
                    if history and len(history) > 1:
                        st.markdown("#### 📊 Price History for this Product")
                        hist_df = pd.DataFrame(history)
                        hist_df["date_recorded"] = pd.to_datetime(hist_df["date_recorded"])

                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=hist_df["date_recorded"],
                            y=hist_df["price"],
                            mode="lines+markers",
                            line=dict(color="#22c55e", width=3, shape="spline"),
                            marker=dict(size=8, color="#6366f1", line=dict(width=2, color="#22c55e")),
                            fill="tozeroy",
                            fillcolor="rgba(34, 197, 94, 0.08)",
                        ))
                        fig.update_layout(
                            template="plotly_dark",
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            xaxis=dict(gridcolor="rgba(56, 189, 248, 0.1)", title="Date"),
                            yaxis=dict(gridcolor="rgba(56, 189, 248, 0.1)", title="Price (₱)", tickprefix="₱"),
                            margin=dict(l=0, r=0, t=20, b=0),
                            height=300,
                        )
                        st.plotly_chart(fig, use_container_width=True)
