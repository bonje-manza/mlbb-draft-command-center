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


def inject_app_styles():
    st.markdown(
        """
        <style>
        :root {
            --cc-bg: #f4efe4;
            --cc-panel: #fbf7ef;
            --cc-panel-strong: #f0e5cf;
            --cc-ink: #17211f;
            --cc-muted: #5f6f6a;
            --cc-accent: #0f766e;
            --cc-accent-2: #bf5b04;
            --cc-danger: #9f1239;
            --cc-border: rgba(23, 33, 31, 0.10);
            --cc-shadow: 0 18px 40px rgba(23, 33, 31, 0.08);
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(15, 118, 110, 0.16), transparent 34%),
                radial-gradient(circle at top right, rgba(191, 91, 4, 0.14), transparent 28%),
                linear-gradient(180deg, #fcfaf5 0%, var(--cc-bg) 58%, #efe7d8 100%);
            color: var(--cc-ink);
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        .cc-hero {
            padding: 1.45rem 1.5rem;
            border-radius: 22px;
            border: 1px solid var(--cc-border);
            background: linear-gradient(135deg, rgba(251, 247, 239, 0.92), rgba(240, 229, 207, 0.88));
            box-shadow: var(--cc-shadow);
            margin-bottom: 1rem;
        }

        .cc-hero h1 {
            margin: 0;
            font-size: 2.35rem;
            line-height: 1.02;
            letter-spacing: -0.03em;
            color: var(--cc-ink);
        }

        .cc-hero p {
            margin: 0.65rem 0 0;
            max-width: 58rem;
            color: var(--cc-muted);
            font-size: 1rem;
        }

        .cc-strip {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.85rem;
            margin: 1rem 0 0.35rem;
        }

        .cc-kpi {
            background: rgba(255, 255, 255, 0.62);
            border: 1px solid var(--cc-border);
            border-radius: 18px;
            padding: 0.95rem 1rem;
        }

        .cc-kpi-label {
            font-size: 0.74rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--cc-muted);
        }

        .cc-kpi-value {
            margin-top: 0.35rem;
            font-size: 1.55rem;
            font-weight: 700;
            line-height: 1;
            color: var(--cc-ink);
        }

        .cc-panel {
            background: rgba(251, 247, 239, 0.9);
            border: 1px solid var(--cc-border);
            border-radius: 20px;
            padding: 1rem;
            box-shadow: var(--cc-shadow);
            height: 100%;
        }

        .cc-panel-title {
            font-size: 0.78rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--cc-muted);
            margin-bottom: 0.5rem;
        }

        .cc-panel-heading {
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--cc-ink);
            margin-bottom: 0.35rem;
        }

        .cc-pick-grid {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 0.7rem;
            margin-top: 0.85rem;
        }

        .cc-slot {
            min-height: 112px;
            border-radius: 18px;
            border: 1px solid var(--cc-border);
            background: rgba(255, 255, 255, 0.65);
            padding: 0.8rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .cc-slot-friendly {
            background: linear-gradient(180deg, rgba(15, 118, 110, 0.12), rgba(255, 255, 255, 0.72));
        }

        .cc-slot-enemy {
            background: linear-gradient(180deg, rgba(159, 18, 57, 0.12), rgba(255, 255, 255, 0.72));
        }

        .cc-slot-index {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--cc-muted);
        }

        .cc-slot-hero {
            font-size: 1rem;
            font-weight: 700;
            color: var(--cc-ink);
            line-height: 1.15;
            margin-top: 0.55rem;
        }

        .cc-slot-meta {
            color: var(--cc-muted);
            font-size: 0.78rem;
            line-height: 1.35;
            margin-top: 0.25rem;
        }

        .cc-slot-empty {
            color: var(--cc-muted);
            font-size: 0.88rem;
            margin-top: 1rem;
        }

        .cc-score-list {
            display: grid;
            gap: 0.65rem;
        }

        .cc-score-row {
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.6);
            border: 1px solid var(--cc-border);
            padding: 0.8rem 0.9rem;
        }

        .cc-score-topline {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 0.45rem;
        }

        .cc-score-name {
            font-weight: 700;
            color: var(--cc-ink);
        }

        .cc-score-value {
            color: var(--cc-muted);
            font-weight: 700;
        }

        .cc-score-bar {
            height: 8px;
            border-radius: 999px;
            background: rgba(23, 33, 31, 0.08);
            overflow: hidden;
        }

        .cc-score-bar > span {
            display: block;
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, var(--cc-accent), #14b8a6);
        }

        .cc-score-detail {
            margin-top: 0.5rem;
            color: var(--cc-muted);
            font-size: 0.83rem;
        }

        .cc-lane-stack {
            display: grid;
            gap: 0.65rem;
            margin-top: 0.8rem;
        }

        .cc-lane-pill {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            padding: 0.7rem 0.85rem;
            border-radius: 14px;
            border: 1px solid var(--cc-border);
            background: rgba(255, 255, 255, 0.6);
        }

        .cc-lane-name {
            color: var(--cc-muted);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }

        .cc-lane-hero {
            font-weight: 700;
            color: var(--cc-ink);
            text-align: right;
        }

        .cc-priority-grid {
            display: grid;
            gap: 0.8rem;
        }

        .cc-priority-card {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.72), rgba(240, 229, 207, 0.88));
            border: 1px solid var(--cc-border);
            border-radius: 18px;
            padding: 0.95rem 1rem;
            box-shadow: var(--cc-shadow);
        }

        .cc-priority-topline {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            align-items: flex-start;
        }

        .cc-priority-rank {
            color: var(--cc-muted);
            font-size: 0.74rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }

        .cc-priority-hero {
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--cc-ink);
        }

        .cc-priority-role {
            color: var(--cc-muted);
            font-size: 0.82rem;
            margin-top: 0.18rem;
        }

        .cc-priority-score {
            font-size: 1.3rem;
            font-weight: 700;
            color: var(--cc-accent);
            white-space: nowrap;
        }

        .cc-priority-meta {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin: 0.65rem 0 0.7rem;
        }

        .cc-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            border-radius: 999px;
            padding: 0.28rem 0.55rem;
            background: rgba(23, 33, 31, 0.06);
            color: var(--cc-ink);
            font-size: 0.76rem;
            font-weight: 600;
        }

        .cc-priority-why {
            color: var(--cc-muted);
            font-size: 0.84rem;
            line-height: 1.45;
        }

        .cc-callout {
            border-radius: 18px;
            border: 1px solid var(--cc-border);
            background: linear-gradient(135deg, rgba(15, 118, 110, 0.12), rgba(255, 255, 255, 0.68));
            padding: 0.9rem 1rem;
            margin-bottom: 0.85rem;
        }

        .cc-callout strong {
            display: block;
            color: var(--cc-ink);
            margin-bottom: 0.25rem;
        }

        @media (max-width: 1100px) {
            .cc-strip,
            .cc-pick-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 700px) {
            .cc-strip,
            .cc-pick-grid {
                grid-template-columns: 1fr;
            }
            .cc-hero h1 {
                font-size: 1.8rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
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


def render_pick_panel(title, selection_df, side_label):
    slots = []
    for slot_index in range(5):
        if slot_index < len(selection_df):
            row = selection_df.iloc[slot_index]
            slot_body = (
                f"<div class='cc-slot cc-slot-{side_label}'>"
                f"<div class='cc-slot-index'>Slot {slot_index + 1}</div>"
                f"<div class='cc-slot-hero'>{row['Hero']}</div>"
                f"<div class='cc-slot-meta'>{row['Role']}<br>{row['Primary Lane']}</div>"
                f"</div>"
            )
        else:
            slot_body = (
                f"<div class='cc-slot cc-slot-{side_label}'>"
                f"<div class='cc-slot-index'>Slot {slot_index + 1}</div>"
                f"<div class='cc-slot-empty'>Waiting for lock-in</div>"
                f"</div>"
            )
        slots.append(slot_body)

    st.markdown(
        (
            "<div class='cc-panel'>"
            f"<div class='cc-panel-title'>{side_label.title()} Side</div>"
            f"<div class='cc-panel-heading'>{title}</div>"
            f"<div class='cc-pick-grid'>{''.join(slots)}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_hero_selector_panel(title, subtitle, key_prefix, options, max_selections):
    st.markdown(
        (
            "<div class='cc-panel'>"
            f"<div class='cc-panel-title'>{title}</div>"
            f"<div class='cc-panel-heading'>{subtitle}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    return st.multiselect(
        label=title,
        options=options,
        max_selections=max_selections,
        label_visibility="collapsed",
        key=f"{key_prefix}_draft_selector",
    )


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
    lane_assignment = team_analysis["lane_assignment"]
    lane_rows = []
    for lane_name in REQUIRED_LANES:
        assigned_hero = next(
            (hero_name for hero_name, assigned_lane in lane_assignment.items() if assigned_lane == lane_name),
            None,
        )
        lane_rows.append(
            "<div class='cc-lane-pill'>"
            f"<div class='cc-lane-name'>{lane_name}</div>"
            f"<div class='cc-lane-hero'>{assigned_hero or 'Open'}</div>"
            "</div>"
        )

    footer = (
        "Open lanes: " + ", ".join(team_analysis["missing_lanes"])
        if team_analysis["missing_lanes"]
        else "All five lanes are covered."
    )
    st.markdown(
        (
            "<div class='cc-panel'>"
            "<div class='cc-panel-title'>Lane Plan</div>"
            "<div class='cc-panel-heading'>Projected Assignment</div>"
            f"<div class='cc-lane-stack'>{''.join(lane_rows)}</div>"
            f"<div class='cc-score-detail'>{footer}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_header_strip(meta_df):
    s_tier_count = int(meta_df[meta_df["Meta Tier"] == "S-Tier (Absolute Meta / Must Ban)"].shape[0])
    hottest = meta_df.nlargest(1, "Contest Rate (%)").iloc[0]
    st.markdown(
        (
            "<div class='cc-hero'>"
            "<div class='cc-panel-title'>Live Draft Console</div>"
            "<h1>Draft faster. Scan less. Lock better.</h1>"
            "<p>The command board now leads with the next decision: your current structure, your best follow-up picks, and the bans most likely to punish a weak draft.</p>"
            "<div class='cc-strip'>"
            f"<div class='cc-kpi'><div class='cc-kpi-label'>Heroes Tracked</div><div class='cc-kpi-value'>{len(meta_df)}</div></div>"
            f"<div class='cc-kpi'><div class='cc-kpi-label'>S-Tier Pressure</div><div class='cc-kpi-value'>{s_tier_count}</div></div>"
            f"<div class='cc-kpi'><div class='cc-kpi-label'>Most Contested</div><div class='cc-kpi-value'>{hottest['Hero']}</div></div>"
            f"<div class='cc-kpi'><div class='cc-kpi-label'>Contest Rate</div><div class='cc-kpi-value'>{hottest['Contest Rate (%)']:.2f}%</div></div>"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_score_cards(team_analysis, draft_size):
    strip_items = [
        ("Draft Score", f"{team_analysis['team_score']}/100"),
        ("Average Power", f"{team_analysis['average_power']:.1f}"),
        ("Average Contest", f"{team_analysis['average_contest']:.2f}%"),
        ("Draft Progress", f"{draft_size}/5"),
    ]
    markup = "".join(
        f"<div class='cc-kpi'><div class='cc-kpi-label'>{label}</div><div class='cc-kpi-value'>{value}</div></div>"
        for label, value in strip_items
    )
    st.markdown(f"<div class='cc-strip'>{markup}</div>", unsafe_allow_html=True)
    st.caption(team_analysis["summary"])


def render_structure_scores(team_analysis):
    rows = []
    for category in team_analysis["categories"]:
        rows.append(
            "<div class='cc-score-row'>"
            "<div class='cc-score-topline'>"
            f"<div class='cc-score-name'>{category['label']}</div>"
            f"<div class='cc-score-value'>{category['score']}/100</div>"
            "</div>"
            f"<div class='cc-score-bar'><span style='width: {category['score']}%'></span></div>"
            f"<div class='cc-score-detail'>{category['detail']}</div>"
            "</div>"
        )

    st.markdown(
        (
            "<div class='cc-panel'>"
            "<div class='cc-panel-title'>Structure Scan</div>"
            "<div class='cc-panel-heading'>What the comp looks like right now</div>"
            f"<div class='cc-score-list'>{''.join(rows)}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_priority_cards(title, subtitle, recommendations, score_column, accent_text):
    st.markdown(
        (
            "<div class='cc-panel'>"
            f"<div class='cc-panel-title'>{title}</div>"
            f"<div class='cc-panel-heading'>{subtitle}</div>"
            f"<div class='cc-score-detail'>{accent_text}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    if not recommendations:
        st.info("No recommendations available for the current draft state.")
        return

    card_markup = []
    for index, recommendation in enumerate(recommendations[:3], start=1):
        card_markup.append(
            "<div class='cc-priority-card'>"
            "<div class='cc-priority-topline'>"
            f"<div><div class='cc-priority-rank'>Priority {index}</div><div class='cc-priority-hero'>{recommendation['Hero']}</div><div class='cc-priority-role'>{recommendation['Role']}</div></div>"
            f"<div class='cc-priority-score'>{recommendation[score_column]:.1f}</div>"
            "</div>"
            "<div class='cc-priority-meta'>"
            f"<span class='cc-chip'>{recommendation['Primary Lane']}</span>"
            f"<span class='cc-chip'>Power {recommendation['True Power Score']:.1f}</span>"
            f"<span class='cc-chip'>Contest {recommendation['Contest Rate (%)']:.2f}%</span>"
            "</div>"
            f"<div class='cc-priority-why'>{'; '.join(recommendation['Why'])}</div>"
            "</div>"
        )

    st.markdown(f"<div class='cc-priority-grid'>{''.join(card_markup)}</div>", unsafe_allow_html=True)


def render_quick_calls(team_analysis, next_pick_recommendations, ban_recommendations):
    priority_pick = next_pick_recommendations[0]["Hero"] if next_pick_recommendations else "No pick available"
    priority_ban = ban_recommendations[0]["Hero"] if ban_recommendations else "No ban target available"
    open_lanes = ", ".join(team_analysis["missing_lanes"]) if team_analysis["missing_lanes"] else "No open lanes"

    st.markdown(
        (
            "<div class='cc-callout'>"
            f"<strong>Pick now: {priority_pick}</strong>"
            f"Best immediate value based on your current structural gaps and meta power. Open lanes: {open_lanes}."
            "</div>"
            "<div class='cc-callout'>"
            f"<strong>Ban now: {priority_ban}</strong>"
            "Highest-pressure removal based on meta threat, flexibility, and how exposed your current draft is."
            "</div>"
        ),
        unsafe_allow_html=True,
    )


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
inject_app_styles()

if meta_df.empty:
    st.stop()

hero_list = meta_df["Hero"].sort_values().tolist()
render_header_strip(meta_df)

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

st.markdown("## Draft Command Center")
draft_col, enemy_col = st.columns(2)
with draft_col:
    selected_team = render_hero_selector_panel(
        "Your Draft",
        "Lock your five picks in order.",
        "friendly",
        hero_list,
        5,
    )
with enemy_col:
    selected_enemy = render_hero_selector_panel(
        "Enemy Draft",
        "Track the opposing side as picks are revealed.",
        "enemy",
        hero_list,
        5,
    )

overlap = sorted(set(selected_team).intersection(selected_enemy))
if overlap:
    st.error("A hero cannot be locked on both sides. Remove duplicates: " + ", ".join(overlap))
    st.stop()

team_df = build_selection_df(meta_df, selected_team)
enemy_df = build_selection_df(meta_df, selected_enemy)

team_display_col, enemy_display_col = st.columns(2)
with team_display_col:
    render_pick_panel("Your Locked Heroes", team_df, "friendly")
with enemy_display_col:
    render_pick_panel("Enemy Locked Heroes", enemy_df, "enemy")

command_tab, breakdown_tab, explorer_tab = st.tabs([
    "Command Board",
    "Draft Breakdown",
    "Meta Explorer",
])

if selected_team:
    team_analysis = analyze_team(team_df)
    next_pick_recommendations = recommend_next_picks(meta_df, team_df, enemy_df, limit=5)
    ban_recommendations = recommend_bans(meta_df, team_df, enemy_df, limit=5)
    render_score_cards(team_analysis, len(selected_team))

    with command_tab:
        quick_col, score_col, lane_col = st.columns([1.1, 1.15, 0.95])
        with quick_col:
            render_quick_calls(team_analysis, next_pick_recommendations, ban_recommendations)
        with score_col:
            render_structure_scores(team_analysis)
        with lane_col:
            render_lane_assignment(team_analysis)

        recommendation_col, ban_col = st.columns(2)
        with recommendation_col:
            if len(selected_team) >= 5:
                st.info("Your side is already full. Remove a lock to reopen next-pick recommendations.")
            else:
                render_priority_cards(
                    "Next Pick Priorities",
                    "The fastest way to close your current draft gaps.",
                    next_pick_recommendations,
                    "Recommendation Score",
                    "Lead with the highest-value pick instead of scanning the full table first.",
                )
        with ban_col:
            render_priority_cards(
                "Ban Priorities",
                "The removals most likely to punish your current shape.",
                ban_recommendations,
                "Threat Score",
                "Ban pressure is ranked by meta threat and how badly each hero stresses your draft.",
            )

    with breakdown_tab:
        risk_col, pick_table_col, ban_table_col = st.columns([0.95, 1.15, 1.15])
        with risk_col:
            st.markdown("### Draft Risks")
            for issue in team_analysis["issues"]:
                render_issue(issue)
            if not team_analysis["issues"]:
                st.success("No structural draft issues detected.")
        with pick_table_col:
            st.markdown("### Next Pick Queue")
            if len(selected_team) >= 5:
                st.info("Your draft is full.")
            else:
                st.dataframe(
                    format_recommendations(next_pick_recommendations, "Recommendation Score"),
                    width="stretch",
                    hide_index=True,
                )
        with ban_table_col:
            st.markdown("### Ban Queue")
            st.dataframe(
                format_recommendations(ban_recommendations, "Threat Score"),
                width="stretch",
                hide_index=True,
            )
else:
    with command_tab:
        st.info("Start by locking your own heroes to generate draft analysis, next-pick suggestions, and ban targets.")
    with breakdown_tab:
        st.info("Detailed breakdown appears once you have at least one hero locked.")

with explorer_tab:
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
            width="stretch",
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