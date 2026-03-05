import streamlit as st
import pandas as pd
import json
import os
import datetime

st.set_page_config(
    page_title="MLBB Immortal Command Center",
    page_icon="None",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data
def load_meta_data():
    try:
        return pd.read_csv("current_mlbb_meta_api.csv")
    except FileNotFoundError:
        st.error("Data source missing. Please run the synchronization script.")
        return pd.DataFrame()

df = load_meta_data()

# --- DATA ENRICHMENT: Role & Lane Database ---
@st.cache_data
def load_role_database():
    try:
        with open('hero_roles.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        st.warning("Role database unavailable. Using default role mappings.")
        return {}

@st.cache_data
def load_lane_database():
    try:
        with open('hero_lanes.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        st.warning("Lane database unavailable. Using default lane mappings.")
        return {}

role_database = load_role_database()
lane_database = load_lane_database()

if not df.empty:
    # Strip any invisible spaces to ensure perfect matching
    df['Hero'] = df['Hero'].astype(str).str.strip()
    df['Role'] = df['Hero'].map(role_database).fillna("Flex/Unknown")
    
    # Extract Primary and Secondary Lanes
    df['Primary Lane'] = df['Hero'].apply(lambda x: lane_database.get(x, {}).get('primary', 'Unknown'))
    df['Secondary Lane'] = df['Hero'].apply(lambda x: lane_database.get(x, {}).get('secondary', None))
    df['All Lanes'] = df.apply(lambda row: [row['Primary Lane']] + ([row['Secondary Lane']] if row['Secondary Lane'] else []), axis=1)

    # Grab the alphabetical list of all heroes for use in selectors
    hero_list = df['Hero'].sort_values().tolist()

st.title("Mythical Glory+ Drafting Intelligence")
st.markdown("Advanced tactical analysis of the current Mobile Legends competitive landscape. Optimized for high-level draft strategy.")

if not df.empty:
    # --- SIDEBAR: Meta Overview ---
    st.sidebar.header("Meta Snapshot")
    st.sidebar.metric(label="Total Heroes Analyzed", value=len(df))
    
    s_tier_count = len(df[df['Meta Tier'] == "S-Tier (Absolute Meta / Must Ban)"])
    st.sidebar.metric(label="High-Priority Threats (S-Tier)", value=s_tier_count)
    
    # --- Last Updated Timestamp ---
    try:
        timestamp = os.path.getmtime("current_mlbb_meta_api.csv")
        last_updated = datetime.datetime.fromtimestamp(timestamp).strftime('%B %d, %Y at %I:%M %p')
        st.sidebar.caption(f"Last Updated: {last_updated}")
    except Exception:
        st.sidebar.caption("Last Updated: Unknown")
    
    st.sidebar.divider()
    
    # --- Tactical Filters ---
    st.sidebar.markdown("### Tactical Filters")
    available_roles = ["All Roles", "Assassin", "Fighter", "Mage", "Marksman", "Support", "Tank", "Flex/Unknown"]
    selected_role = st.sidebar.selectbox("Filter by Primary Role:", available_roles)
    
    available_lanes = ["All Lanes", "Mid Lane", "Gold Lane", "EXP Lane", "Jungler", "Roamer"]
    selected_lane = st.sidebar.selectbox("Filter by Recommended Lane:", available_lanes)
    
    st.sidebar.divider()
    
    # --- Top 3 Most Contested ---
    st.sidebar.markdown("### Most Contested Heroes")
    top_3 = df.nlargest(3, 'Contest Rate (%)')
    for index, row in top_3.iterrows():
        st.sidebar.markdown(f"**{row['Hero']}** ({row['Contest Rate (%)']}%)")

    # --- ADMINISTRATIVE CONTROLS ---
    st.sidebar.divider()
    with st.sidebar.expander("Administrative Controls"):
        st.info("Authorized personnel only.")
        admin_pass = st.text_input("Authorization Token:", type="password")
        
        if admin_pass == "Glory2026":
            st.session_state['is_admin'] = True
            st.success("Administrative access granted.")
        else:
            st.session_state['is_admin'] = False

        if st.session_state.get('is_admin'):
            st.divider()
            st.markdown("### Data Synchronization")
            new_api_url = st.text_input("API Endpoint URL:", placeholder="https://api.gms.moontontech.com/api/...")
            
            if st.button("Update Data Source"):
                if new_api_url:
                    with st.spinner("Synchronizing with remote server..."):
                        # Import the backend dynamically so Streamlit can use it
                        from meta_scout import get_mlbb_meta_api, analyze_meta
                        
                        raw_data = get_mlbb_meta_api(new_api_url)
                        if not raw_data.empty:
                            analyzed_meta = analyze_meta(raw_data)
                            analyzed_meta.to_csv("current_mlbb_meta_api.csv", index=False)
                            st.cache_data.clear() 
                            st.success("Synchronization successful. Local database updated.")
                            st.rerun() 
                        else:
                            st.error("Synchronization failed. Invalid response from endpoint.")
                else:
                    st.error("API URL required.")

            st.divider()
            st.markdown("### Hero Lane Management")
            
            manage_hero = st.selectbox("Select Hero to Configure:", options=hero_list)
            
            if manage_hero:
                current_p = lane_database.get(manage_hero, {}).get('primary', 'Unknown')
                current_s = lane_database.get(manage_hero, {}).get('secondary', None)
                
                lane_options = ["Mid Lane", "Gold Lane", "EXP Lane", "Jungler", "Roamer"]
                secondary_options = [None] + lane_options
                
                # Find index for default values
                try: p_idx = lane_options.index(current_p)
                except ValueError: p_idx = 0
                
                try: s_idx = secondary_options.index(current_s)
                except ValueError: s_idx = 0
                
                new_primary = st.selectbox("Primary Lane:", options=lane_options, index=p_idx)
                new_secondary = st.selectbox("Secondary Lane:", options=secondary_options, index=s_idx)
                
                if st.button("Save Tactical Update"):
                    lane_database[manage_hero] = {
                        "primary": new_primary,
                        "secondary": new_secondary
                    }
                    try:
                        with open('hero_lanes.json', 'w', encoding='utf-8') as f:
                            json.dump(lane_database, f, indent=4)
                        st.cache_data.clear()
                        st.success(f"Tactical profile for {manage_hero} updated.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to save update: {e}")
    # --- END ADMINISTRATIVE CONTROLS ---

    # --- MAIN CONSOLE: TEAM SYNERGY ANALYZER ---
    st.subheader("Team Synergy Analyzer")
    st.markdown("Analyze win conditions and potential vulnerabilities for your selected draft.")
    
    selected_team = st.multiselect("Draft Selection (Up to 5 Heroes):", options=hero_list, max_selections=5)
    
    if selected_team:
        # Preserve selection order visually
        team_df = df[df['Hero'].isin(selected_team)].set_index('Hero').reindex(selected_team).reset_index()
        team_roles = team_df['Role'].tolist()
        team_lanes = team_df['All Lanes'].tolist()
        
        # Display the drafted team visually
        cols = st.columns(5)
        for i, row in team_df.iterrows():
            with cols[i]:
                st.info(f"**{row['Hero']}**\n\n*{row['Role']}*\n\n`{row['Primary Lane']}`")
        
        # --- SYNERGY ANALYSIS ---
        warnings = []
        
        # 1. Frontline Check
        frontline = team_roles.count('Tank') + team_roles.count('Fighter')
        if frontline == 0:
            warnings.append("**VULNERABILITY: NO FRONTLINE.** Lack of defensive utility may compromise objective control.")
            
        # 2. Magic Damage Check
        magic = team_roles.count('Mage')
        # Hardcoding the exceptions: Magic-damage assassins/fighters
        magic_flex = ['Aamon', 'Gusion', 'Joy', 'Karina', 'Harley', 'Julian', 'Guinevere', 'Silvanna']
        has_magic_flex = any(hero in selected_team for hero in magic_flex)
        
        if magic >= 3:
            warnings.append("**VULNERABILITY: EXCESSIVE MAGIC DAMAGE.** Enemy defensive itemization can easily mitigate overall team output.")
        elif magic == 0 and not has_magic_flex and len(selected_team) >= 3:
            warnings.append("**VULNERABILITY: LACK OF MAGIC DAMAGE.** Entirely physical composition allows enemies to stack armor efficiently.")
            
        # 3. Squishy / Scaling Check
        mm_count = team_roles.count('Marksman')
        if mm_count > 1:
            warnings.append("**VULNERABILITY: LOW DURABILITY.** Multiple Marksmen increase vulnerability to early-game aggression.")
        elif mm_count == 0 and len(selected_team) == 5:
            warnings.append("**ADVISORY: NO LATE-GAME CARRY.** Lacking a primary Marksman may hinder high-ground siege potential.")

        # 4. Lane Coverage Check
        if len(selected_team) == 5:
            required_lanes = ["Mid Lane", "Gold Lane", "EXP Lane", "Jungler", "Roamer"]
            # Check if we can assign each hero to a unique required lane
            # This is a simplified check: does the union of all possible lanes for these 5 heroes cover all 5 required lanes?
            # A more robust check would use a matching algorithm, but for MLBB most heroes have clear roles.
            covered_lanes = set()
            for lanes in team_lanes:
                for lane in lanes:
                    covered_lanes.add(lane)
            
            missing_lanes = [lane for lane in required_lanes if lane not in covered_lanes]
            if missing_lanes:
                warnings.append(f"**VULNERABILITY: INCOMPLETE LANE COVERAGE.** Missing: {', '.join(missing_lanes)}.")
            
        # Display the tactical report - Only show critical errors once 5 heroes are picked
        if len(selected_team) == 5:
            if warnings:
                for w in warnings:
                    st.warning(w)
            else:
                st.success("COMPOSITION BALANCED: Selection provides a stable mix of frontline presence, damage types, and scaling.")
        else:
            st.info(f"Drafting in progress ({len(selected_team)}/5). Analysis will finalize upon full selection.")
            
    st.divider()

    # --- TIER LIST & DATA VISUALIZATION ---
    st.subheader("Hero Performance and Tier Rankings")
    
    # Tactical Search Override
    search_query = st.text_input("Quick Search Hero:", placeholder="Search by name...").strip().title()
    
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
            return 'color: #2E7D32; font-weight: bold;' # Professional Forest Green
        elif val >= 50.0:
            return 'color: #4CAF50;' # standard green
        elif val < 48.0:
            return 'color: #C62828; font-weight: bold;' # Professional Deep Red
        else:
            return 'color: #EF5350;' # standard red

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

            # Apply Lane Filter
            if selected_lane != "All Lanes":
                tier_df = tier_df[tier_df['All Lanes'].apply(lambda x: selected_lane in x)]
                
            # Apply Search Filter (if active)
            if search_query:
                tier_df = tier_df[tier_df['Hero'].str.contains(search_query, case=False, na=False)]
            
            if not tier_df.empty:
                if tab_name != "All Heroes":
                    tier_df = tier_df.drop(columns=['Meta Tier'])
                
                cols = ['True Overall Rank', 'Hero', 'Role', 'Primary Lane', 'Secondary Lane', 'Meta Tier', 'True Power Score', 'Contest Rate (%)', 'Ban Rate', 'Pick Rate', 'Win Rate']
                existing_cols = [c for c in cols if c in tier_df.columns]
                tier_df = tier_df[existing_cols]
                
                # Apply Pandas Styling
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
                        "Primary Lane": st.column_config.TextColumn("Primary Lane"),
                        "Secondary Lane": st.column_config.TextColumn("Secondary Lane"),
                        "Meta Tier": st.column_config.TextColumn("Meta Tier"),
                        "True Power Score": st.column_config.NumberColumn("Power Score", format="%.1f"),
                        "Contest Rate (%)": st.column_config.ProgressColumn(
                            "Contest Rate",
                            format="%.2f%%",
                            min_value=0,
                            max_value=100,
                        ),
                        "Ban Rate": st.column_config.NumberColumn("Ban Rate", format="%.2f%%"),
                        "Pick Rate": st.column_config.NumberColumn("Pick Rate", format="%.2f%%"),
                        "Win Rate": st.column_config.Column("Win Rate")
                    }
                )
            else:
                if search_query:
                    st.info(f"No results found for '{search_query}' in the {tab_name} category.")
                else:
                    st.info(f"No data available for the selected filters.")