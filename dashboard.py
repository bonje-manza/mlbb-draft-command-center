import streamlit as st
import pandas as pd
import json
import os
import datetime

st.set_page_config(
    page_title="MLBB Immortal Command Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data
def load_meta_data():
    try:
        return pd.read_csv("current_mlbb_meta_api.csv")
    except FileNotFoundError:
        st.error("Intelligence file missing! Please run 'meta_scout.py' first.")
        return pd.DataFrame()

df = load_meta_data()

# --- DATA ENRICHMENT: The Hardcoded Role Database ---
@st.cache_data
def load_role_database():
    try:
        with open('hero_roles.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        st.warning("Role database missing! Using fallback roles.")
        return {}

role_database = load_role_database()

if not df.empty:
    # Strip any invisible spaces to ensure perfect matching
    df['Hero'] = df['Hero'].astype(str).str.strip()
    df['Role'] = df['Hero'].map(role_database).fillna("Flex/Unknown")

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
    
    # --- Tactical Filters ---
    st.sidebar.markdown("### 🎯 Tactical Filters")
    available_roles = ["All Roles", "Assassin", "Fighter", "Mage", "Marksman", "Support", "Tank", "Flex/Unknown"]
    selected_role = st.sidebar.selectbox("Filter by Primary Role:", available_roles)
    
    st.sidebar.divider()
    
    # --- Top 3 Most Contested ---
    st.sidebar.markdown("### Top 3 Most Contested")
    top_3 = df.nlargest(3, 'Contest Rate (%)')
    for index, row in top_3.iterrows():
        st.sidebar.markdown(f"**{row['Hero']}** - {row['Contest Rate (%)']}%")

        # --- 🔐 ADMIN OVERRIDE PANEL ---
    st.sidebar.divider()
    with st.sidebar.expander("🔐 Admin Override (API Patch)"):
        st.warning("Update the API endpoint if Moonton shifts the data feed.")
        new_api_url = st.text_input("New Endpoint URL:", placeholder="https://api.gms.moontontech.com/api/...")
        admin_pass = st.text_input("Passcode:", type="password")
        
        if st.button("Execute Infiltration"):
            if admin_pass == "Glory2026": # You can change this passcode
                if new_api_url:
                    with st.spinner("Bypassing Moonton firewalls..."):
                        # Import the backend dynamically so Streamlit can use it
                        from meta_scout import get_mlbb_meta_api, analyze_meta
                        
                        raw_data = get_mlbb_meta_api(new_api_url)
                        if not raw_data.empty:
                            analyzed_meta = analyze_meta(raw_data)
                            analyzed_meta.to_csv("current_mlbb_meta_api.csv", index=False)
                            st.cache_data.clear() # Force Streamlit to drop the old data
                            st.success("Target acquired! Live database overwritten.")
                            st.rerun() # Refresh the page immediately
                        else:
                            st.error("Infiltration failed. Verify the URL syntax.")
                else:
                    st.error("Missing target URL.")
            else:
                st.error("Access Denied.")

    # --- MAIN CONSOLE: THE TEAM SYNERGY ANALYZER ---
    st.subheader("🛠️ Live Team Synergy Analyzer")
    st.markdown("Draft your squad to instantly analyze win conditions and critical weaknesses.")
    
    # Grab the alphabetical list of all heroes for the dropdown
    hero_list = df['Hero'].sort_values().tolist()
    selected_team = st.multiselect("Select up to 5 heroes for your team:", options=hero_list, max_selections=5)
    
    if selected_team:
        # Preserve selection order visually
        team_df = df[df['Hero'].isin(selected_team)].set_index('Hero').reindex(selected_team).reset_index()
        team_roles = team_df['Role'].tolist()
        
        # Display the drafted team visually
        cols = st.columns(5)
        for i, row in team_df.iterrows():
            with cols[i]:
                st.info(f"**{row['Hero']}**\n\n*{row['Role']}*")
        
        # --- THE SYNERGY ALGORITHM ---
        warnings = []
        
        # 1. Frontline Check
        frontline = team_roles.count('Tank') + team_roles.count('Fighter')
        if frontline == 0:
            warnings.append("🚨 **NO FRONTLINE:** You have 0 Tanks or Fighters. You will instantly lose Turtle and Lord fights.")
            
        # 2. Magic Damage Check
        magic = team_roles.count('Mage')
        # Hardcoding the exceptions: Magic-damage assassins/fighters
        magic_flex = ['Aamon', 'Gusion', 'Joy', 'Karina', 'Harley', 'Julian', 'Guinevere', 'Silvanna']
        has_magic_flex = any(hero in selected_team for hero in magic_flex)
        
        if magic >= 3:
            warnings.append("⚠️ **TOO MUCH MAGIC:** The enemy will build Radiant Armor and Athena's Shield to completely negate your damage.")
        elif magic == 0 and not has_magic_flex and len(selected_team) >= 3:
            warnings.append("⚠️ **FULL PHYSICAL (AD):** Your team lacks Magic Damage. The enemy will build Antique Cuirass and become unkillable.")
            
        # 3. Squishy / Scaling Check
        mm_count = team_roles.count('Marksman')
        if mm_count > 1:
            warnings.append("🚨 **TOO SQUISHY:** Multiple Marksmen makes your team incredibly vulnerable to early-game invades.")
        elif mm_count == 0 and len(selected_team) == 5:
            warnings.append("⚠️ **NO LATE-GAME CARRY:** You lack a Marksman. If the game goes past 15 minutes, you will struggle to push high-ground towers.")
            
        # Display the tactical report - Only show critical errors once 5 heroes are picked
        if len(selected_team) == 5:
            if warnings:
                for w in warnings:
                    st.error(w)
            else:
                st.success("✅ **PERFECT BALANCE:** Your draft has a lethal mix of frontline secure, split damage, and scaling potential.")
        else:
            st.info(f"Drafting in progress ({len(selected_team)}/5)... Keep picking to see your final synergy report.")
            
    st.divider()

    # --- THE TIER LIST TABS & DATA VISUALIZATION ---
    st.subheader("🗂️ Hero Tiers & True Power Rankings")
    
    # Tactical Search Override
    search_query = st.text_input("🔍 Quick Search Hero:", placeholder="Type a hero name... (e.g., Ling, Gloo)").strip().title()
    
    tier_categories = [
        "S-Tier (Absolute Meta / Must Ban)",
        "A-Tier (Comfort Staple)",
        "Hidden OP (The Specialist)",
        "B-Tier (Reliable / Strong)",
        "C-Tier (Situational / Average)",
        "Solo-Queue Trap (Avoid at all costs)",
        "D-Tier (Out of Meta / Weak)"
    ]
    
    tab_names = ["All Heroes"] + [tier.split(" (")[0] for tier in tier_categories]
    tabs = st.tabs(tab_names)
    
    # Styling function for Win Rate
    def color_win_rate(val):
        if val >= 52.0:
            return 'color: #00FF00; font-weight: bold;' # Bright Green for high win rate
        elif val >= 50.0:
            return 'color: #90EE90;' # Light green for positive
        elif val < 48.0:
            return 'color: #FF4500; font-weight: bold;' # Red for terrible win rate
        else:
            return 'color: #FFA07A;' # Light red for slightly negative

    for i, tab_name in enumerate(tab_names):
        with tabs[i]:
            if tab_name == "All Heroes":
                tier_df = df.copy()
            else:
                full_tier_name = tier_categories[i - 1] 
                tier_df = df[df['Meta Tier'] == full_tier_name].copy()
            
            # Apply Role Filter
            if selected_role != "All Roles":
                tier_df = tier_df[tier_df['Role'] == selected_role]
                
            # Apply Search Filter (if active)
            if search_query:
                tier_df = tier_df[tier_df['Hero'].str.contains(search_query, case=False, na=False)]
            
            if not tier_df.empty:
                if tab_name != "All Heroes":
                    tier_df = tier_df.drop(columns=['Meta Tier'])
                
                cols = ['True Overall Rank', 'Hero', 'Role', 'Meta Tier', 'True Power Score', 'Contest Rate (%)', 'Ban Rate', 'Pick Rate', 'Win Rate']
                existing_cols = [c for c in cols if c in tier_df.columns]
                tier_df = tier_df[existing_cols]
                
                # Apply Pandas Styling to the dataframe before passing to Streamlit
                styled_df = tier_df.style.map(color_win_rate, subset=['Win Rate']).format(
                    {"Win Rate": "{:.2f}%"}
                )
                
                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "True Overall Rank": st.column_config.NumberColumn("Rank", format="%d"),
                        "Hero": st.column_config.TextColumn("Hero"),
                        "Role": st.column_config.TextColumn("Role"),
                        "Meta Tier": st.column_config.TextColumn("Meta Tier"),
                        "True Power Score": st.column_config.NumberColumn("Power Score", format="%.1f"),
                        "Contest Rate (%)": st.column_config.ProgressColumn(
                            "Threat Level (Contest)",
                            format="%.2f%%",
                            min_value=0,
                            max_value=100,
                        ),
                        "Ban Rate": st.column_config.NumberColumn("Ban Rate", format="%.2f%%"),
                        "Pick Rate": st.column_config.NumberColumn("Pick Rate", format="%.2f%%"),
                        "Win Rate": st.column_config.Column("Win Rate") # Formatted via pandas styling above
                    }
                )
            else:
                if search_query:
                    st.info(f"No results found for '{search_query}' in the {tab_name} category.")
                else:
                    st.info(f"No {selected_role}s currently fall into the {tab_name} category.")