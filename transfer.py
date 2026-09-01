"""
Demo Web App — Search with Line of Business & Unique ID filters
Run with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# Page config
# ---------------------------------------------------------
st.set_page_config(page_title="Business Search Demo", layout="wide")

# ---------------------------------------------------------
# Sample data (replace with your real data source / DB query)
# ---------------------------------------------------------
@st.cache_data
def load_data():
    data = {
        "Unique ID": ["ID-1001", "ID-1002", "ID-1003", "ID-1004", "ID-1005", "ID-1006"],
        "Line of Business": ["Retail", "Wealth Management", "Retail", "Insurance", "Wealth Management", "Insurance"],
        "Customer Name": ["Alice Perkins", "Brian Cole", "Carla Diaz", "David Chen", "Elena Rossi", "Farhan Khan"],
        "Status": ["Active", "Pending", "Active", "Closed", "Active", "Pending"],
        "Region": ["West", "North", "South", "East", "West", "North"],
    }
    return pd.DataFrame(data)

df = load_data()

# ---------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------
st.sidebar.header("Filters")

lob_options = ["All"] + sorted(df["Line of Business"].unique().tolist())
selected_lob = st.sidebar.selectbox("Line of Business", lob_options)

id_options = ["All"] + sorted(df["Unique ID"].unique().tolist())
selected_id = st.sidebar.selectbox("Unique ID", id_options)

filtered_df = df.copy()
if selected_lob != "All":
    filtered_df = filtered_df[filtered_df["Line of Business"] == selected_lob]
if selected_id != "All":
    filtered_df = filtered_df[filtered_df["Unique ID"] == selected_id]

# ---------------------------------------------------------
# Main area — centered search box
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    .search-title {
        text-align: center;
        font-size: 28px;
        font-weight: 600;
        margin-top: 40px;
        margin-bottom: 20px;
    }
    div[data-testid="stTextInput"] {
        max-width: 600px;
        margin: 0 auto;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="search-title">🔍 Search Records</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    search_term = st.text_input("", placeholder="Search by name, ID, region, status...", label_visibility="collapsed")

if search_term:
    mask = filtered_df.apply(
        lambda row: row.astype(str).str.contains(search_term, case=False, na=False).any(),
        axis=1,
    )
    filtered_df = filtered_df[mask]

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# Results
# ---------------------------------------------------------
st.write(f"**{len(filtered_df)}** result(s) found")
st.dataframe(filtered_df, use_container_width=True, hide_index=True)
