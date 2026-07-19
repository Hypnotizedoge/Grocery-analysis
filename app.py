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
    initial_sidebar_state="collapsed",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* ── Import Google Font & Material Icons ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0');
    @import url('https://fonts.googleapis.com/icon?family=Material+Icons');

    
    /* ── Hide native Streamlit UI elements ── */
    [data-testid="collapsedControl"],
    [data-testid="stHeader"] {
        display: none !important;
    }

    /* ── Global ── */
    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif;
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

# ─── Main Header & Store Selection ───────────────────────────────────────────

st.markdown('<div class="hero-title">Grocery Price Tracker</div>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">Track prices across stores</p>', unsafe_allow_html=True)
st.markdown("")

stores = db.get_stores()
store_names = [s["name"] for s in stores]
store_map = {s["name"]: s["id"] for s in stores}

selected_store_name = None
selected_store_id = None

@st.dialog("Add New Store")
def add_store_dialog():
    new_store_name = st.text_input("Store Name", key="new_store_input")
    if st.button("Add Store", key="add_store_btn", use_container_width=True):
        if new_store_name.strip():
            try:
                db.add_store(new_store_name)
                st.success(f"Added **{new_store_name}**")
                st.rerun()
            except Exception as e:
                st.error(f"Store already exists or error: {e}")
        else:
            st.warning("Enter a store name")

# Show a horizontal layout for store selection
col_store, col_add = st.columns([2, 1])

with col_store:
    if stores:
        selected_store_name = st.selectbox(
            "Select Store",
            options=store_names,
            key="store_selector"
        )
        selected_store_id = store_map[selected_store_name]
        st.session_state.selected_store_id = selected_store_id
    else:
        st.info("**Welcome!** Add your first grocery store to get started.")

with col_add:
    st.markdown("<br>", unsafe_allow_html=True) # For vertical alignment with the selectbox
    if st.button("Add New Store", use_container_width=True):
        add_store_dialog()

st.markdown("---")


# ── Tabs ──
tab_entry, tab_update = st.tabs([
    "🆕 Add New Product",
    "🔄 Update Price",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: ADD NEW PRODUCT
# ═══════════════════════════════════════════════════════════════════════════════

with tab_entry:
    st.markdown("### 🆕 Add New Product")
    st.caption(f"Store: **{selected_store_name if selected_store_id else 'None'}** &nbsp;•&nbsp; Date: **{date.today().strftime('%B %d, %Y')}**")

    if not selected_store_id:
        st.info("👈 Select a store from the sidebar first.")
    else:
        tesseract_ok, tesseract_msg = check_tesseract()
        if not tesseract_ok:
            st.warning("OCR (Tesseract) is not configured correctly. You can still enter prices manually.")

        st.markdown("#### 1. Product Details")
        col1, col2 = st.columns(2)
        with col1:
            category_option = st.selectbox("Select Category *", options=db.get_categories(), key="entry_cat")
        with col2:
            custom_category = st.text_input("Or Type Custom Category", key="entry_custom_cat", placeholder="e.g. Snacks")
        
        final_category = custom_category.strip() if custom_category.strip() else category_option

        item_name = st.text_input("Item Name *", key="entry_item")

        col3, col4 = st.columns(2)
        with col3:
            existing_brands = db.get_brands()
            brand_option = st.selectbox("Select Existing Brand", options=["(No brand / Generic)"] + existing_brands, key="entry_brand")
        with col4:
            custom_brand = st.text_input("Or Type New Brand", key="entry_custom_brand", placeholder="e.g. Nestle")
        
        final_brand = custom_brand.strip() if custom_brand.strip() else ("" if brand_option == "(No brand / Generic)" else brand_option)

        col5, col6 = st.columns([2, 1])
        with col5:
            weight_volume = st.text_input("Weight / Volume", key="entry_weight", placeholder="e.g. 250, 1.5")
        with col6:
            unit = st.selectbox("Unit", options=["g", "kg", "mL", "L", "pcs", "pack", "box", "can", "bottle", "sachet", "oz", "lb"], key="entry_unit")

        st.markdown("---")
        st.markdown("#### 2. Capture Initial Price")
        
        input_method = st.radio(
            "Capture method",
            options=["Take Photo", "Upload Image File", "Manual Entry Only"],
            horizontal=True,
            key="add_input_method",
            label_visibility="collapsed",
        )

        image = None
        detected_price = 0.0

        if input_method == "Take Photo":
            camera_image = st.camera_input("Point camera at the price label", key="add_cam")
            if camera_image is not None:
                from PIL import Image
                image = Image.open(camera_image)
        elif input_method == "Upload Image File":
            uploaded_file = st.file_uploader("Upload price label photo", type=["jpg", "jpeg", "png", "bmp", "webp"], key="add_upload")
            if uploaded_file is not None:
                from PIL import Image
                image = Image.open(uploaded_file)

        if image is not None:
            if tesseract_ok:
                with st.spinner("🔍 Reading price label..."):
                    _, _ = preprocess_image(image)
                    extracted = extract_text(image)
                    detected_prices = detect_prices_from_text(extracted)
                
                col_img, col_result = st.columns([1, 1.5])
                with col_img:
                    st.image(image, use_container_width=True)
                with col_result:
                    if detected_prices:
                        detected_price = detected_prices[0]
                        st.markdown(f'''
                        <div style="background: rgba(34,197,94,0.15); border: 2px solid rgba(34,197,94,0.4); border-radius: 20px; padding: 28px; text-align: center; margin-bottom: 12px;">
                            <div style="color: #86efac; font-size: 0.85rem; font-weight: 600; text-transform: uppercase;">💰 Detected Price</div>
                            <div style="color: #22c55e; font-size: 3.2rem; font-weight: 800; line-height: 1;">RM {detected_price:,.2f}</div>
                        </div>
                        ''', unsafe_allow_html=True)
                        
                        if st.button(f"Save New Product at RM {detected_price:,.2f} Now", type="primary", use_container_width=True, key="add_quick_save_btn"):
                            if not item_name.strip():
                                st.error("Item name is required above.")
                            else:
                                new_id = db.add_product(
                                    category=final_category,
                                    item_name=item_name,
                                    brand=final_brand,
                                    weight_volume=weight_volume,
                                    unit=unit,
                                )
                                db.add_price(new_id, selected_store_id, detected_price)
                                st.success(f"Saved {item_name} at RM {detected_price:.2f}")
                                st.rerun()

                        if len(detected_prices) > 1:
                            st.caption(f"Other numbers found: {', '.join([f'RM {p:,.2f}' for p in detected_prices[1:]])}")
                    else:
                        st.info("⚠️ No Price Detected. Enter manually below.")
            else:
                st.image(image, use_container_width=True, caption="Image captured (OCR disabled)")

        st.markdown("---")
        st.markdown("#### 3. Save Product")
        
        final_price = st.number_input(
            "Final Price (RM ) *",
            min_value=0.0,
            value=float(detected_price) if detected_price > 0 else 0.0,
            step=0.25,
            format="%.2f",
            key="add_final_price",
        )

        st.markdown("")
        if st.button("Save New Product", use_container_width=True, type="primary"):
            if not item_name.strip():
                st.error("Item name is required.")
            elif final_price <= 0:
                st.error("Price must be greater than 0.")
            else:
                new_id = db.add_product(
                    category=final_category,
                    item_name=item_name,
                    brand=final_brand,
                    weight_volume=weight_volume,
                    unit=unit,
                )
                db.add_price(new_id, selected_store_id, final_price)
                st.success(f"Saved **{item_name}** at **RM {final_price:.2f}**")
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: UPDATE PRICE
# ═══════════════════════════════════════════════════════════════════════════════

with tab_update:
    st.markdown("### 🔄 Update Price")
    st.caption(f"Store: **{selected_store_name if selected_store_id else 'None'}** &nbsp;•&nbsp; Date: **{date.today().strftime('%B %d, %Y')}**")

    if not selected_store_id:
        st.info("👈 Select a store from the sidebar first.")
    else:
        tesseract_ok, _ = check_tesseract()
        
        st.markdown("#### 1. Select Product")
        existing_products = db.get_products(store_id=selected_store_id)
        if not existing_products:
            st.info("No products yet. Use **Add New Product**.")
        else:
            product_options_update = {
                f"{p['item_name']} — {p['brand']} ({p['weight_volume']} {p['unit']}) | Current: RM {float(p['latest_price']) if p['latest_price'] else 0:.2f}".strip(): p["id"]
                for p in existing_products
            }
            selected_update = st.selectbox(
                "Product",
                options=list(product_options_update.keys()),
                key="update_select",
                placeholder="Search and select a product...",
            )
            
            if selected_update:
                product_id_to_update = product_options_update[selected_update]
                product_info = db.get_product_by_id(product_id_to_update, selected_store_id)
                default_price_from_existing = product_info["latest_price"] if product_info["latest_price"] else 0.0

                st.markdown(f'''
                <div class="glass-card">
                    <strong style="color: #38bdf8;">{product_info['item_name']}</strong>
                    <span style="color: #64748b;"> — {product_info['brand']}</span><br>
                    <span style="color: #94a3b8;">💰 Last price at this store:
                    <strong style="color: #22c55e;">RM {default_price_from_existing:.2f}</strong></span>
                </div>
                ''', unsafe_allow_html=True)

                st.markdown("---")
                st.markdown("#### 2. Capture New Price")
                
                up_input_method = st.radio(
                    "Capture method",
                    options=["Take Photo", "Upload Image File", "Manual Entry Only"],
                    horizontal=True,
                    key="up_input_method",
                    label_visibility="collapsed",
                )

                up_image = None
                up_detected_price = 0.0

                if up_input_method == "Take Photo":
                    up_camera_image = st.camera_input("Point camera at the price label", key="up_cam")
                    if up_camera_image is not None:
                        from PIL import Image
                        up_image = Image.open(up_camera_image)
                elif up_input_method == "Upload Image File":
                    up_uploaded_file = st.file_uploader("Upload price label photo", type=["jpg", "jpeg", "png", "bmp", "webp"], key="up_upload")
                    if up_uploaded_file is not None:
                        from PIL import Image
                        up_image = Image.open(up_uploaded_file)

                if up_image is not None:
                    if tesseract_ok:
                        with st.spinner("🔍 Reading price label..."):
                            _, _ = preprocess_image(up_image)
                            up_extracted = extract_text(up_image)
                            up_detected_prices = detect_prices_from_text(up_extracted)
                        
                        col_img, col_result = st.columns([1, 1.5])
                        with col_img:
                            st.image(up_image, use_container_width=True)
                        with col_result:
                            if up_detected_prices:
                                up_detected_price = up_detected_prices[0]
                                st.markdown(f'''
                                <div style="background: rgba(34,197,94,0.15); border: 2px solid rgba(34,197,94,0.4); border-radius: 20px; padding: 28px; text-align: center; margin-bottom: 12px;">
                                    <div style="color: #86efac; font-size: 0.85rem; font-weight: 600; text-transform: uppercase;">💰 Detected Price</div>
                                    <div style="color: #22c55e; font-size: 3.2rem; font-weight: 800; line-height: 1;">RM {up_detected_price:,.2f}</div>
                                </div>
                                ''', unsafe_allow_html=True)
                                
                                if st.button(f"Save RM {up_detected_price:,.2f} Now", type="primary", use_container_width=True, key="up_quick_save_btn"):
                                    db.update_price_today(product_id_to_update, selected_store_id, up_detected_price)
                                    st.success(f"Price updated to RM {up_detected_price:.2f} for today.")
                                    st.rerun()
                                    
                            else:
                                st.info("⚠️ No Price Detected. Enter manually below.")
                    else:
                        st.image(up_image, use_container_width=True, caption="Image captured")

                st.markdown("---")
                st.markdown("#### 3. Save Price")
                
                up_final_price = st.number_input(
                    "Final Price (RM ) *",
                    min_value=0.0,
                    value=float(up_detected_price) if up_detected_price > 0 else float(default_price_from_existing),
                    step=0.25,
                    format="%.2f",
                    key="up_final_price",
                )

                if st.button("💾 Update Price", use_container_width=True, type="primary"):
                    if up_final_price <= 0:
                        st.error("Price must be greater than 0.")
                    else:
                        db.update_price_today(product_id_to_update, selected_store_id, up_final_price)
                        st.success(f"Price updated to **RM {up_final_price:.2f}** for today.")
                        st.rerun()

                # Price History Chart
                history = db.get_price_history(product_id_to_update, selected_store_id)
                if history and len(history) > 1:
                    st.markdown("---")
                    st.markdown("#### 📈 Price History at this Store")
                    import plotly.graph_objects as go
                    hist_df = pd.DataFrame(history)
                    hist_df["date"] = pd.to_datetime(hist_df["date"])

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=hist_df["date"],
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
                        yaxis=dict(gridcolor="rgba(56, 189, 248, 0.1)", title="Price (RM )", tickprefix="RM "),
                        margin=dict(l=0, r=0, t=20, b=0),
                        height=300,
                    )
                    st.plotly_chart(fig, use_container_width=True)
