import streamlit as st
import pandas as pd
import json
import os
import datetime

# 1. Page Configuration: Setting up the layout for an ultrawide monitor
st.set_page_config(
    page_title="MLBB Immortal Command Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Loading the Intelligence
# The @st.cache_data decorator tells Streamlit to only load the CSV once, 
# keeping the dashboard lightning-fast when you switch tabs.
@st.cache_data
def load_meta_data():
    try:
        return pd.read_csv("current_mlbb_meta_api.csv")
    except FileNotFoundError:
        st.error("Intelligence file missing! Please run 'meta_scout.py' first to extract the latest data.")
        return pd.DataFrame()

df = load_meta_data()

# 3. The Dashboard UI
st.title("🏆 Mythical Glory+ Drafting Intelligence")
st.markdown("Live tactical hierarchy of the current Mobile Legends patch. **Sort, filter, and draft with mathematical precision.**")

if not df.empty:
    # --- SIDEBAR: The Analyst's Summary ---
    st.sidebar.header("Current Meta Snapshot")
    st.sidebar.metric(label="Total Heroes Analyzed", value=len(df))
    
    s_tier_count = len(df[df['Meta Tier'] == "S-Tier (Absolute Meta / Must Ban)"])
    st.sidebar.metric(label="Critical Threats (S-Tier)", value=s_tier_count)
    
    # --- Last Updated Timestamp ---
    try:
        timestamp = os.path.getmtime("current_mlbb_meta_api.csv")
        last_updated = datetime.datetime.fromtimestamp(timestamp).strftime('%B %d, %Y at %I:%M %p')
        st.sidebar.caption(f"🔄 **Last Updated:** {last_updated}")
    except Exception:
        st.sidebar.caption("🔄 **Last Updated:** Unknown")
    
    st.sidebar.divider()
    
    # --- Tactical Filters (RESTORED) ---
    st.sidebar.markdown("### 🎯 Tactical Filters")
    available_roles = ["All Roles", "Assassin", "Fighter", "Mage", "Marksman", "Support", "Tank", "Flex/Unknown"]
    selected_role = st.sidebar.selectbox("Filter by Primary Role:", available_roles)
    
    st.sidebar.divider()
    
    # --- Top 3 Most Contested ---
    st.sidebar.markdown("### Top 3 Most Contested")
    top_3 = df.nlargest(3, 'Contest Rate (%)')
    for index, row in top_3.iterrows():
        st.sidebar.markdown(f"**{row['Hero']}** - {row['Contest Rate (%)']}%")

    # --- MAIN CONSOLE: The Tactical Heatmap ---
    st.subheader("🔥 Meta Heatmap: The Most Contested Heroes")
    # A quick bar chart so you can visually scan the biggest draft threats instantly
    top_10_contested = df.nlargest(10, 'Contest Rate (%)')
    chart_data = top_10_contested.set_index('Hero')['Contest Rate (%)']
    st.bar_chart(chart_data, color="#ff4b4b")
    
    st.divider()

    # --- THE DRAFTING TABS ---
    st.subheader("🗂️ Hero Tiers")
    
    # We define the strict hierarchy order
    # We define the strict hierarchy order
    tier_categories = [
        "S-Tier (Absolute Meta / Must Ban)",
        "A-Tier (Comfort Staple)",
        "Hidden OP (The Specialist)",
        "B-Tier (Reliable / Strong)",
        "C-Tier (Situational / Average)",
        "Solo-Queue Trap (Avoid at all costs)",
        "D-Tier (Out of Meta / Weak)"
    ]
    
    # Create clean tab names (stripping away the descriptions)
    tab_names = [tier.split(" (")[0] for tier in tier_categories]
    tabs = st.tabs(tab_names)
    
    # Populate each tab dynamically
    for i, tier_name in enumerate(tier_categories):
        with tabs[i]:
            # Filter the dataframe for this specific tier
            tier_df = df[df['Meta Tier'] == tier_name].copy()
            
            if not tier_df.empty:
                # Drop the 'Meta Tier' column since the tab name already tells us the tier
                tier_df = tier_df.drop(columns=['Meta Tier'])
                
                # Display the interactive, sortable table
                st.dataframe(
                    tier_df,
                    use_container_width=True,
                    hide_index=True,
                    # We can use Pandas Styler inside Streamlit to highlight the win rates
                    column_config={
                        "Win Rate": st.column_config.NumberColumn(
                            "Win Rate (%)",
                            format="%.2f",
                        ),
                        "Contest Rate (%)": st.column_config.ProgressColumn(
                            "Threat Level (Contest Rate)",
                            format="%.2f%%",
                            min_value=0,
                            max_value=100,
                        )
                    }
                )
            else:
                st.info(f"No heroes currently fall into the {tab_names[i]} category.")

