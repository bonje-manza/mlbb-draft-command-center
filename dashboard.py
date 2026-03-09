import datetime
import json
import os

import pandas as pd
import streamlit as st

from draft_engine import REQUIRED_LANES, analyze_team, recommend_bans, recommend_next_picks
from meta_scout import API_ENDPOINT_ENV, REQUIRED_API_TOKEN_ENV, analyze_meta, get_mlbb_meta_api

DATA_FILE = "current_mlbb_meta_api.csv"
ROLE_FILE = "hero_roles.json"
LANE_FILE = "hero_lanes.json"
ADMIN_PASSWORD_ENV = "MLBB_ADMIN_PASSWORD"
REQUIRED_COLUMNS = {
    "True Overall Rank",
    "Hero",
    "Meta Tier",
    "True Power Score",
    "Contest Rate (%)",
    "Ban Rate",
    "Pick Rate",
    "Win Rate",
}
NUMERIC_COLUMNS = [
    "True Overall Rank",
    "True Power Score",
    "Contest Rate (%)",
    "Ban Rate",
    "Pick Rate",
    "Win Rate",
]

st.set_page_config(
    page_title="MLBB Immortal Command Center",
    page_icon="None",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def load_meta_data():
    try:
        meta_df = pd.read_csv(DATA_FILE)
    except FileNotFoundError:
        st.error("Data source missing. Run the synchronization script or the approved admin sync.")
        return pd.DataFrame()
    except Exception as exc:
        st.error(f"Unable to load the local meta dataset: {exc}")
        return pd.DataFrame()

    missing_columns = REQUIRED_COLUMNS.difference(meta_df.columns)
    if missing_columns:
        st.error(
            "Dataset is missing required fields: "
            + ", ".join(sorted(missing_columns))
            + ". Run synchronization again."
        )
        return pd.DataFrame()

    meta_df = meta_df.copy()
    meta_df["Hero"] = meta_df["Hero"].astype(str).str.strip()
    meta_df = meta_df[meta_df["Hero"] != ""]
    meta_df = meta_df.drop_duplicates(subset=["Hero"], keep="first")

    for column_name in NUMERIC_COLUMNS:
        meta_df[column_name] = pd.to_numeric(meta_df[column_name], errors="coerce")

    meta_df = meta_df.dropna(subset=["Hero", "True Power Score", "Contest Rate (%)", "Ban Rate", "Pick Rate", "Win Rate"])
    meta_df["True Overall Rank"] = meta_df["True Overall Rank"].astype(int)
    meta_df["True Power Score"] = meta_df["True Power Score"].round(1)
    for column_name in ["Contest Rate (%)", "Ban Rate", "Pick Rate", "Win Rate"]:
        meta_df[column_name] = meta_df[column_name].round(2)

    return meta_df.sort_values(by=["True Overall Rank", "Hero"]).reset_index(drop=True)


@st.cache_data
def load_role_database():
    try:
        with open(ROLE_FILE, "r", encoding="utf-8") as file_handle:
            return json.load(file_handle)
    except Exception:
        st.warning("Role database unavailable. Unmapped heroes will fall back to Flex/Unknown.")
        return {}


@st.cache_data
def load_lane_database():
    try:
        with open(LANE_FILE, "r", encoding="utf-8") as file_handle:
            return json.load(file_handle)
    except Exception:
        st.warning("Lane database unavailable. Unmapped heroes will fall back to Unknown.")
        return {}


def enrich_meta_data(meta_df, role_database, lane_database):
    if meta_df.empty:
        return meta_df

    enriched_df = meta_df.copy()
    enriched_df["Role"] = enriched_df["Hero"].map(role_database).fillna("Flex/Unknown")
    enriched_df["Primary Lane"] = enriched_df["Hero"].apply(
        lambda hero_name: lane_database.get(hero_name, {}).get("primary", "Unknown")
    )
    enriched_df["Secondary Lane"] = enriched_df["Hero"].apply(
        lambda hero_name: lane_database.get(hero_name, {}).get("secondary")
    )
    enriched_df["All Lanes"] = enriched_df.apply(
        lambda row: [
            lane_name for lane_name in [row["Primary Lane"], row["Secondary Lane"]]
            if lane_name and lane_name != "Unknown"
        ],
        axis=1,
    )
    return enriched_df


def build_selection_df(meta_df, selected_heroes):
    if not selected_heroes:
        return meta_df.iloc[0:0].copy()

    return (
        meta_df[meta_df["Hero"].isin(selected_heroes)]
        .set_index("Hero")
        .reindex(selected_heroes)
        .reset_index()
    )


def render_hero_cards(title, selection_df):
    st.markdown(f"### {title}")
    if selection_df.empty:
        st.caption("No heroes locked yet.")
        return

    columns = st.columns(5)
    for index, (_, row) in enumerate(selection_df.iterrows()):
        with columns[index % 5]:
            st.info(f"**{row['Hero']}**\n\n{row['Role']}\n\n{row['Primary Lane']}")


def render_issue(issue):
    message = f"**{issue['title']}**\n\n{issue['detail']}"
    if issue["severity"] == "error":
        st.error(message)
    elif issue["severity"] == "warning":
        st.warning(message)
    else:
        st.info(message)


def format_recommendations(recommendations, score_column):
    if not recommendations:
        return pd.DataFrame()

    formatted_df = pd.DataFrame(recommendations).copy()
    formatted_df["Why"] = formatted_df["Why"].apply(lambda reasons: "; ".join(reasons))
    ordered_columns = [
        "Hero",
        "Role",
        "Primary Lane",
        score_column,
        "True Power Score",
        "Contest Rate (%)",
        "Why",
    ]
    return formatted_df[ordered_columns]


def render_lane_assignment(team_analysis):
    st.markdown("### Projected Lane Plan")
    lane_assignment = team_analysis["lane_assignment"]
    if not lane_assignment:
        st.caption("No clean lane assignment is possible yet.")
    else:
        for lane_name in REQUIRED_LANES:
            assigned_hero = next(
                (hero_name for hero_name, assigned_lane in lane_assignment.items() if assigned_lane == lane_name),
                None,
            )
            if assigned_hero:
                st.markdown(f"**{lane_name}:** {assigned_hero}")
            else:
                st.markdown(f"**{lane_name}:** Open")

    if team_analysis["missing_lanes"]:
        st.caption("Open lanes: " + ", ".join(team_analysis["missing_lanes"]))
    else:
        st.caption("All five lanes are covered.")


def handle_admin_actions(hero_list, lane_database):
    admin_password = os.getenv(ADMIN_PASSWORD_ENV)

    with st.sidebar.expander("Administrative Controls"):
        if not admin_password:
            st.caption(f"Admin controls disabled. Set {ADMIN_PASSWORD_ENV} to enable them.")
            return

        entered_password = st.text_input("Authorization Token", type="password")
        is_admin = bool(entered_password) and entered_password == admin_password

        if entered_password and not is_admin:
            st.error("Authorization failed.")
            return

        if not is_admin:
            st.caption("Authorized personnel only.")
            return

        st.success("Administrative access granted.")
        st.markdown("### Data Synchronization")

        approved_endpoint = os.getenv(API_ENDPOINT_ENV)
        sync_ready = bool(approved_endpoint and os.getenv(REQUIRED_API_TOKEN_ENV))
        if sync_ready:
            st.caption(f"Approved endpoint: {approved_endpoint}")
            if st.button("Sync Approved Data Source"):
                with st.spinner("Synchronizing with approved source..."):
                    raw_data = get_mlbb_meta_api()
                    if raw_data.empty:
                        st.error("Synchronization failed. Verify the approved endpoint and API token.")
                    else:
                        analyzed_meta = analyze_meta(raw_data)
                        analyzed_meta.to_csv(DATA_FILE, index=False)
                        st.cache_data.clear()
                        st.success("Synchronization successful. Local database updated.")
                        st.rerun()
        else:
            st.warning(
                f"Synchronization is disabled until both {API_ENDPOINT_ENV} and {REQUIRED_API_TOKEN_ENV} are configured."
            )

        st.divider()
        st.markdown("### Hero Lane Management")
        selected_hero = st.selectbox("Select Hero to Configure", options=hero_list)
        current_primary = lane_database.get(selected_hero, {}).get("primary", "Unknown")
        current_secondary = lane_database.get(selected_hero, {}).get("secondary")

        lane_options = REQUIRED_LANES.copy()
        secondary_options = [None] + lane_options

        try:
            primary_index = lane_options.index(current_primary)
        except ValueError:
            primary_index = 0

        try:
            secondary_index = secondary_options.index(current_secondary)
        except ValueError:
            secondary_index = 0

        new_primary = st.selectbox("Primary Lane", options=lane_options, index=primary_index)
        new_secondary = st.selectbox("Secondary Lane", options=secondary_options, index=secondary_index)

        if st.button("Save Tactical Update"):
            lane_database[selected_hero] = {
                "primary": new_primary,
                "secondary": new_secondary,
            }
            try:
                with open(LANE_FILE, "w", encoding="utf-8") as file_handle:
                    json.dump(lane_database, file_handle, indent=4)
                st.cache_data.clear()
                st.success(f"Tactical profile for {selected_hero} updated.")
                st.rerun()
            except Exception as exc:
                st.error(f"Failed to save update: {exc}")


def color_win_rate(value):
    if value >= 52.0:
        return "color: #1b5e20; font-weight: bold;"
    if value >= 50.0:
        return "color: #2e7d32;"
    if value < 48.0:
        return "color: #b71c1c; font-weight: bold;"
    return "color: #d84315;"


meta_df = enrich_meta_data(load_meta_data(), load_role_database(), load_lane_database())

st.title("Mythical Glory+ Drafting Intelligence")
st.markdown(
    "Decision support for MLBB drafts: lane coverage, role balance, next-pick recommendations, and ban pressure in one view."
)

if meta_df.empty:
    st.stop()

hero_list = meta_df["Hero"].sort_values().tolist()

st.sidebar.header("Meta Snapshot")
st.sidebar.metric("Total Heroes Analyzed", len(meta_df))
st.sidebar.metric(
    "High-Priority Threats (S-Tier)",
    int(meta_df[meta_df["Meta Tier"] == "S-Tier (Absolute Meta / Must Ban)"].shape[0]),
)

try:
    timestamp = os.path.getmtime(DATA_FILE)
    last_updated = datetime.datetime.fromtimestamp(timestamp).strftime("%B %d, %Y at %I:%M %p")
    st.sidebar.caption(f"Last Updated: {last_updated}")
except Exception:
    st.sidebar.caption("Last Updated: Unknown")

st.sidebar.divider()
st.sidebar.markdown("### Tactical Filters")
available_roles = ["All Roles"] + sorted(meta_df["Role"].dropna().unique().tolist())
selected_role = st.sidebar.selectbox("Filter by Role", available_roles)
available_lanes = ["All Lanes"] + REQUIRED_LANES
selected_lane = st.sidebar.selectbox("Filter by Lane", available_lanes)
search_query = st.sidebar.text_input("Quick Search Hero", placeholder="Search by name...").strip()

st.sidebar.divider()
st.sidebar.markdown("### Most Contested Heroes")
for _, row in meta_df.nlargest(5, "Contest Rate (%)").iterrows():
    st.sidebar.markdown(f"**{row['Hero']}** ({row['Contest Rate (%)']:.2f}%)")

handle_admin_actions(hero_list, load_lane_database())

st.subheader("Draft Command Center")
draft_col, enemy_col = st.columns(2)
with draft_col:
    selected_team = st.multiselect("Your Draft (up to 5 heroes)", options=hero_list, max_selections=5)
with enemy_col:
    selected_enemy = st.multiselect("Enemy Draft (up to 5 heroes)", options=hero_list, max_selections=5)

overlap = sorted(set(selected_team).intersection(selected_enemy))
if overlap:
    st.error("A hero cannot be locked on both sides. Remove duplicates: " + ", ".join(overlap))
    st.stop()

team_df = build_selection_df(meta_df, selected_team)
enemy_df = build_selection_df(meta_df, selected_enemy)

team_display_col, enemy_display_col = st.columns(2)
with team_display_col:
    render_hero_cards("Your Locked Heroes", team_df)
with enemy_display_col:
    render_hero_cards("Enemy Locked Heroes", enemy_df)

if selected_team:
    team_analysis = analyze_team(team_df)
    next_pick_recommendations = recommend_next_picks(meta_df, team_df, enemy_df, limit=5)
    ban_recommendations = recommend_bans(meta_df, team_df, enemy_df, limit=5)

    overview_columns = st.columns(4)
    overview_columns[0].metric("Draft Score", f"{team_analysis['team_score']}/100")
    overview_columns[1].metric("Average Power", f"{team_analysis['average_power']:.1f}")
    overview_columns[2].metric("Average Contest", f"{team_analysis['average_contest']:.2f}%")
    overview_columns[3].metric("Draft Progress", f"{len(selected_team)}/5")
    st.caption(team_analysis["summary"])

    analysis_col, risk_col, lane_col = st.columns([1.1, 1.2, 1.0])
    with analysis_col:
        st.markdown("### Structure Scores")
        for category in team_analysis["categories"]:
            st.markdown(f"**{category['label']}** ({category['score']}/100)")
            st.progress(category["score"] / 100)
            st.caption(category["detail"])

    with risk_col:
        st.markdown("### Draft Risks")
        for issue in team_analysis["issues"]:
            render_issue(issue)
        if not team_analysis["issues"]:
            st.success("No structural draft issues detected.")

    with lane_col:
        render_lane_assignment(team_analysis)

    recommendation_col, ban_col = st.columns(2)
    with recommendation_col:
        st.markdown("### Best Next Picks")
        if len(selected_team) >= 5:
            st.info("Your side is already full. Adjust locks to see next-pick suggestions.")
        else:
            st.dataframe(
                format_recommendations(next_pick_recommendations, "Recommendation Score"),
                use_container_width=True,
                hide_index=True,
            )

    with ban_col:
        st.markdown("### Recommended Bans")
        st.dataframe(
            format_recommendations(ban_recommendations, "Threat Score"),
            use_container_width=True,
            hide_index=True,
        )
else:
    st.info("Start by locking your own heroes to generate draft analysis, next-pick suggestions, and ban targets.")

st.divider()
st.subheader("Meta Explorer")

filtered_df = meta_df.copy()
if selected_role != "All Roles":
    filtered_df = filtered_df[filtered_df["Role"] == selected_role]
if selected_lane != "All Lanes":
    filtered_df = filtered_df[filtered_df["All Lanes"].apply(lambda lane_names: selected_lane in lane_names)]
if search_query:
    filtered_df = filtered_df[filtered_df["Hero"].str.contains(search_query, case=False, na=False)]

if filtered_df.empty:
    st.info("No heroes match the active filters.")
else:
    explorer_columns = [
        "True Overall Rank",
        "Hero",
        "Role",
        "Primary Lane",
        "Secondary Lane",
        "Meta Tier",
        "True Power Score",
        "Contest Rate (%)",
        "Ban Rate",
        "Pick Rate",
        "Win Rate",
    ]
    explorer_df = filtered_df[explorer_columns].copy()
    styled_df = explorer_df.style.map(color_win_rate, subset=["Win Rate"]).format(
        {
            "True Power Score": "{:.1f}",
            "Contest Rate (%)": "{:.2f}%",
            "Ban Rate": "{:.2f}%",
            "Pick Rate": "{:.2f}%",
            "Win Rate": "{:.2f}%",
        }
    )

    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "True Overall Rank": st.column_config.NumberColumn("Rank", format="%d"),
            "True Power Score": st.column_config.NumberColumn("Power Score", format="%.1f"),
            "Contest Rate (%)": st.column_config.ProgressColumn(
                "Contest Rate",
                min_value=0,
                max_value=100,
                format="%.2f%%",
            ),
            "Ban Rate": st.column_config.NumberColumn("Ban Rate", format="%.2f%%"),
            "Pick Rate": st.column_config.NumberColumn("Pick Rate", format="%.2f%%"),
            "Win Rate": st.column_config.NumberColumn("Win Rate", format="%.2f%%"),
        },
    )