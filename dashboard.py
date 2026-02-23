import streamlit as st
import pandas as pd
import json

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
    # --- SIDEBAR: Filters & Summaries ---
    st.sidebar.header("Current Meta Snapshot")
    st.sidebar.metric(label="Total Heroes Analyzed", value=len(df))
    
    st.sidebar.divider()
    
    st.sidebar.markdown("### 🎯 Tactical Filters")
    available_roles = ["All Roles", "Assassin", "Fighter", "Mage", "Marksman", "Support", "Tank", "Flex/Unknown"]
    selected_role = st.sidebar.selectbox("Filter by Primary Role:", available_roles)
    
    st.sidebar.divider()
    st.sidebar.markdown("### Top 3 Most Contested")
    top_3 = df.nlargest(3, 'Contest Rate (%)')
    for index, row in top_3.iterrows():
        st.sidebar.markdown(f"**{row['Hero']}** - {row['Contest Rate (%)']}%")

    # --- MAIN CONSOLE: THE TEAM SYNERGY ANALYZER ---
    st.subheader("🛠️ Live Team Synergy Analyzer")
    st.markdown("Draft your squad to instantly analyze win conditions and critical weaknesses.")
    
    # Grab the alphabetical list of all heroes for the dropdown
    hero_list = df['Hero'].sort_values().tolist()
    selected_team = st.multiselect("Select up to 5 heroes for your team:", options=hero_list, max_selections=5)
    
    if selected_team:
        team_df = df[df['Hero'].isin(selected_team)]
        team_roles = team_df['Role'].tolist()
        
        # Display the drafted team visually
        cols = st.columns(5)
        for i, (idx, row) in enumerate(team_df.iterrows()):
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
        elif mm_count == 0 and len(selected_team) >= 4:
            warnings.append("⚠️ **NO LATE-GAME CARRY:** You lack a Marksman. If the game goes past 15 minutes, you will struggle to push high-ground towers.")
            
        # Display the tactical report
        if warnings:
            for w in warnings:
                st.error(w)
        elif len(selected_team) == 5:
            st.success("✅ **PERFECT BALANCE:** Your draft has a lethal mix of frontline secure, split damage, and scaling potential.")
        else:
            st.info("Keep drafting to see your final synergy report...")
            
    st.divider()

    # --- THE TIER LIST TABS ---
    st.subheader("🗂️ Hero Tiers")
    
    tier_categories = [
        "S-Tier (Absolute Meta / Must Ban)",
        "A-Tier (Comfort Staple)",
        "Hidden OP (The Specialist)",
        "B-Tier (Reliable / Strong)",
        "C-Tier (Situational / Average)",
        "Solo-Queue Trap (Avoid at all costs)",
        "D-Tier (Out of Meta / Weak)"
    ]
    
    tab_names = [tier.split(" (")[0] for tier in tier_categories]
    tabs = st.tabs(tab_names)
    
    for i, tier_name in enumerate(tier_categories):
        with tabs[i]:
            tier_df = df[df['Meta Tier'] == tier_name].copy()
            
            if selected_role != "All Roles":
                tier_df = tier_df[tier_df['Role'] == selected_role]
            
            if not tier_df.empty:
                tier_df = tier_df.drop(columns=['Meta Tier'])
                cols = ['Hero', 'Role', 'Contest Rate (%)', 'Ban Rate', 'Pick Rate', 'Win Rate', 'True Match Presence (%)']
                existing_cols = [c for c in cols if c in tier_df.columns]
                tier_df = tier_df[existing_cols]
                
                st.dataframe(
                    tier_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Win Rate": st.column_config.NumberColumn("Win Rate (%)", format="%.2f"),
                        "Contest Rate (%)": st.column_config.ProgressColumn(
                            "Threat Level",
                            format="%.2f%%",
                            min_value=0,
                            max_value=100,
                        )
                    }
                )
            else:
                st.info(f"No {selected_role}s currently fall into the {tab_names[i]} category.")