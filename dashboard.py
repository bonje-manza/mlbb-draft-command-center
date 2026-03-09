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
            /* ========================================
               THEME-AWARE COLOR SYSTEM
               Automatically adapts to light/dark mode
            ======================================== */
        
            :root, [data-theme="light"] {
                /* Light Mode Colors */
                --cc-bg-base: #fafaf9;
                --cc-bg-elevated: #ffffff;
                --cc-bg-gradient-1: rgba(14, 165, 233, 0.08);
                --cc-bg-gradient-2: rgba(168, 85, 247, 0.06);
                --cc-surface: rgba(255, 255, 255, 0.85);
                --cc-surface-strong: rgba(250, 250, 249, 0.95);
                --cc-surface-hover: rgba(245, 245, 244, 0.95);
            
                --cc-text-primary: #0a0a0a;
                --cc-text-secondary: #525252;
                --cc-text-muted: #737373;
            
                --cc-border-default: rgba(0, 0, 0, 0.08);
                --cc-border-strong: rgba(0, 0, 0, 0.12);
            
                --cc-accent-primary: #0ea5e9;
                --cc-accent-secondary: #8b5cf6;
                --cc-accent-success: #10b981;
                --cc-accent-warning: #f59e0b;
                --cc-accent-danger: #ef4444;
            
                --cc-friendly: #059669;
                --cc-friendly-bg: rgba(16, 185, 129, 0.12);
                --cc-enemy: #dc2626;
                --cc-enemy-bg: rgba(239, 68, 68, 0.12);
            
                --cc-shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.08);
                --cc-shadow-md: 0 4px 12px rgba(0, 0, 0, 0.10);
                --cc-shadow-lg: 0 10px 30px rgba(0, 0, 0, 0.12);
                --cc-glow: 0 0 20px rgba(14, 165, 233, 0.15);

                --cc-space-xs: 0.5rem;
                --cc-space-sm: 0.75rem;
                --cc-space-md: 1rem;
                --cc-space-lg: 1.25rem;
                --cc-space-xl: 1.5rem;
                --cc-space-2xl: 2rem;
                --cc-top-nav-offset: 3.75rem;
            }

            @media (prefers-color-scheme: dark) {
                :root, [data-theme="dark"] {
                    /* Dark Mode Colors */
                    --cc-bg-base: #0a0a0a;
                    --cc-bg-elevated: #171717;
                    --cc-bg-gradient-1: rgba(14, 165, 233, 0.12);
                    --cc-bg-gradient-2: rgba(168, 85, 247, 0.10);
                    --cc-surface: rgba(23, 23, 23, 0.90);
                    --cc-surface-strong: rgba(38, 38, 38, 0.95);
                    --cc-surface-hover: rgba(64, 64, 64, 0.95);
                
                    --cc-text-primary: #fafafa;
                    --cc-text-secondary: #d4d4d4;
                    --cc-text-muted: #a3a3a3;
                
                    --cc-border-default: rgba(255, 255, 255, 0.10);
                    --cc-border-strong: rgba(255, 255, 255, 0.15);
                
                    --cc-accent-primary: #38bdf8;
                    --cc-accent-secondary: #a78bfa;
                    --cc-accent-success: #34d399;
                    --cc-accent-warning: #fbbf24;
                    --cc-accent-danger: #f87171;
                
                    --cc-friendly: #10b981;
                    --cc-friendly-bg: rgba(16, 185, 129, 0.18);
                    --cc-enemy: #ef4444;
                    --cc-enemy-bg: rgba(239, 68, 68, 0.18);
                
                    --cc-shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.30);
                    --cc-shadow-md: 0 4px 12px rgba(0, 0, 0, 0.40);
                    --cc-shadow-lg: 0 10px 30px rgba(0, 0, 0, 0.50);
                    --cc-glow: 0 0 30px rgba(56, 189, 248, 0.25);
                }
        }

            /* ========================================
               BASE LAYOUT & BACKGROUNDS
            ======================================== */
        
        .stApp {
            background:
                    radial-gradient(circle at 20% 20%, var(--cc-bg-gradient-1), transparent 50%),
                    radial-gradient(circle at 80% 80%, var(--cc-bg-gradient-2), transparent 50%),
                    var(--cc-bg-base);
                color: var(--cc-text-primary);
                transition: background 0.3s ease, color 0.2s ease;
        }

        .block-container {
            padding-top: calc(var(--cc-top-nav-offset) + var(--cc-space-lg));
            padding-bottom: var(--cc-space-2xl);
                max-width: 1600px;
        }

            /* ========================================
               HERO HEADER SECTION
            ======================================== */
        
        .cc-hero {
            padding: var(--cc-space-2xl) calc(var(--cc-space-2xl) + var(--cc-space-xs));
                border-radius: 24px;
                border: 1px solid var(--cc-border-default);
                background: var(--cc-surface-strong);
                backdrop-filter: blur(20px);
                box-shadow: var(--cc-shadow-lg), var(--cc-glow);
            margin-top: var(--cc-space-md);
            margin-bottom: var(--cc-space-xl);
                transition: all 0.3s ease;
        }

        .cc-hero h1 {
            margin: 0;
                font-size: 2.75rem;
                line-height: 1.1;
                letter-spacing: -0.04em;
                background: linear-gradient(135deg, var(--cc-accent-primary), var(--cc-accent-secondary));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                font-weight: 800;
        }

        .cc-hero p {
                margin: 0.75rem 0 0;
                max-width: 60rem;
                color: var(--cc-text-secondary);
                font-size: 1.05rem;
                line-height: 1.6;
        }

            /* ========================================
               KPI METRICS STRIP
            ======================================== */
        
        .cc-strip {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: var(--cc-space-lg);
                margin: var(--cc-space-lg) 0 var(--cc-space-sm);
        }

        .cc-kpi {
                background: var(--cc-surface);
                backdrop-filter: blur(10px);
                border: 1px solid var(--cc-border-default);
                border-radius: 16px;
                padding: 1.25rem 1.5rem;
                transition: all 0.2s ease;
            }
        
            .cc-kpi:hover {
                background: var(--cc-surface-hover);
                box-shadow: var(--cc-shadow-md);
                transform: translateY(-2px);
        }

        .cc-kpi-label {
                font-size: 0.7rem;
            text-transform: uppercase;
                letter-spacing: 0.15em;
                font-weight: 600;
                color: var(--cc-text-muted);
        }

        .cc-kpi-value {
                margin-top: 0.5rem;
                font-size: 2rem;
                font-weight: 800;
                line-height: 1.1;
                color: var(--cc-text-primary);
        }

            /* ========================================
               PANEL COMPONENTS
            ======================================== */
        
        .cc-panel {
                background: var(--cc-surface);
                backdrop-filter: blur(12px);
                border: 1px solid var(--cc-border-default);
            border-radius: 20px;
                padding: var(--cc-space-xl);
                box-shadow: var(--cc-shadow-md);
            height: 100%;
                transition: all 0.3s ease;
            }
        
            .cc-panel:hover {
                border-color: var(--cc-border-strong);
        }

        .cc-panel-title {
                font-size: 0.7rem;
                letter-spacing: 0.15em;
            text-transform: uppercase;
                font-weight: 700;
                color: var(--cc-accent-primary);
                margin-bottom: 0.75rem;
        }

        .cc-panel-heading {
                font-size: 1.35rem;
                font-weight: 800;
                color: var(--cc-text-primary);
                margin-bottom: 0.5rem;
                line-height: 1.3;
        }

            /* ========================================
               DRAFT PICK GRID
            ======================================== */
        
        .cc-pick-grid {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
                gap: var(--cc-space-md);
                margin-top: var(--cc-space-md);
        }

        .cc-slot {
                min-height: 130px;
                border-radius: 16px;
                border: 2px solid var(--cc-border-default);
                background: var(--cc-surface);
                backdrop-filter: blur(8px);
                padding: 1rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
                transition: all 0.2s ease;
            }
        
            .cc-slot:hover {
                transform: scale(1.02);
                box-shadow: var(--cc-shadow-md);
        }

        .cc-slot-friendly {
                background: var(--cc-friendly-bg);
                border-color: var(--cc-friendly);
        }

        .cc-slot-enemy {
                background: var(--cc-enemy-bg);
                border-color: var(--cc-enemy);
        }

        .cc-slot-index {
                font-size: 0.65rem;
            text-transform: uppercase;
                letter-spacing: 0.15em;
                font-weight: 700;
                color: var(--cc-text-muted);
        }

        .cc-slot-hero {
                font-size: 1.1rem;
                font-weight: 800;
                color: var(--cc-text-primary);
                line-height: 1.2;
                margin-top: 0.6rem;
        }

        .cc-slot-meta {
                color: var(--cc-text-muted);
                font-size: 0.8rem;
                line-height: 1.4;
            margin-top: 0.25rem;
        }

        .cc-slot-empty {
                color: var(--cc-text-muted);
                font-size: 0.85rem;
            margin-top: 1rem;
                font-style: italic;
                opacity: 0.7;
        }

            /* ========================================
               SCORE DISPLAY COMPONENTS
            ======================================== */
        
        .cc-score-list {
            display: grid;
                gap: var(--cc-space-md);
        }

        .cc-score-row {
                border-radius: 14px;
                background: var(--cc-bg-elevated);
                border: 1px solid var(--cc-border-default);
                padding: 1rem 1.25rem;
                transition: all 0.2s ease;
            }
        
            .cc-score-row:hover {
                background: var(--cc-surface-hover);
                border-color: var(--cc-border-strong);
        }

        .cc-score-topline {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
                margin-bottom: 0.65rem;
                align-items: center;
        }

        .cc-score-name {
                font-weight: 800;
                font-size: 0.95rem;
                color: var(--cc-text-primary);
        }

        .cc-score-value {
                color: var(--cc-accent-primary);
                font-weight: 800;
                font-size: 1.1rem;
        }

        .cc-score-bar {
                height: 10px;
            border-radius: 999px;
                background: var(--cc-border-default);
            overflow: hidden;
        }

        .cc-score-bar > span {
            display: block;
            height: 100%;
            border-radius: 999px;
                background: linear-gradient(90deg, var(--cc-accent-primary), var(--cc-accent-secondary));
                transition: width 0.5s ease;
        }

        .cc-score-detail {
                margin-top: 0.65rem;
                color: var(--cc-text-secondary);
                font-size: 0.85rem;
                line-height: 1.5;
        }

            /* ========================================
               LANE ASSIGNMENT DISPLAY
            ======================================== */
        
        .cc-lane-stack {
            display: grid;
                gap: var(--cc-space-md);
                margin-top: var(--cc-space-md);
        }

        .cc-lane-pill {
            display: flex;
            justify-content: space-between;
                align-items: center;
            gap: 1rem;
                padding: 0.85rem 1.15rem;
            border-radius: 14px;
                border: 1px solid var(--cc-border-default);
                background: var(--cc-bg-elevated);
                transition: all 0.2s ease;
            }
        
            .cc-lane-pill:hover {
                background: var(--cc-surface-hover);
                border-color: var(--cc-border-strong);
        }

        .cc-lane-name {
                color: var(--cc-text-muted);
                font-size: 0.75rem;
            text-transform: uppercase;
                letter-spacing: 0.12em;
                font-weight: 700;
        }

        .cc-lane-hero {
                font-weight: 800;
                font-size: 0.95rem;
                color: var(--cc-text-primary);
            text-align: right;
        }

            /* ========================================
               PRIORITY RECOMMENDATION CARDS
            ======================================== */
        
        .cc-priority-grid {
            display: grid;
                gap: var(--cc-space-md);
        }

        .cc-priority-card {
                background: var(--cc-surface);
                backdrop-filter: blur(10px);
                border: 1px solid var(--cc-border-default);
            border-radius: 18px;
                padding: 1.25rem 1.5rem;
                box-shadow: var(--cc-shadow-md);
                transition: all 0.2s ease;
            }
        
            .cc-priority-card:hover {
                border-color: var(--cc-accent-primary);
                box-shadow: var(--cc-shadow-lg), var(--cc-glow);
                transform: translateY(-3px);
        }

        .cc-priority-topline {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
                align-items: center;
        }

        .cc-priority-rank {
                color: var(--cc-accent-primary);
                font-size: 0.7rem;
            text-transform: uppercase;
                letter-spacing: 0.15em;
                font-weight: 700;
        }

        .cc-priority-hero {
                font-size: 1.35rem;
                font-weight: 800;
                color: var(--cc-text-primary);
                margin-top: 0.25rem;
        }

        .cc-priority-role {
                color: var(--cc-text-secondary);
                font-size: 0.85rem;
                margin-top:0.25rem;
        }

        .cc-priority-score {
                font-size: 2rem;
                font-weight: 800;
                color: var(--cc-accent-primary);
            white-space: nowrap;
                line-height: 1;
        }

        .cc-priority-meta {
            display: flex;
                gap: 0.6rem;
            flex-wrap: wrap;
                margin: 0.85rem 0;
        }

        .cc-chip {
            display: inline-flex;
            align-items: center;
                gap: 0.4rem;
            border-radius: 999px;
                padding: 0.4rem 0.85rem;
                background: var(--cc-bg-elevated);
                border: 1px solid var(--cc-border-default);
                color: var(--cc-text-secondary);
                font-size: 0.75rem;
                font-weight: 700;
                transition: all 0.2s ease;
            }
        
            .cc-chip:hover {
                background: var(--cc-surface-hover);
                border-color: var(--cc-accent-primary);
                color: var(--cc-accent-primary);
        }

        .cc-priority-why {
                color: var(--cc-text-secondary);
                font-size: 0.88rem;
                line-height: 1.6;
                margin-bottom: 0.5rem;
        }

            /* ========================================
               EXPLAINABILITY CARDS
            ======================================== */
        
        .cc-explain-stack {
            display: grid;
                gap: var(--cc-space-md);
                margin-top: var(--cc-space-md);
        }

        .cc-explain-card {
            border-radius: 16px;
                border: 1px solid var(--cc-border-default);
                background: var(--cc-bg-elevated);
                padding: 1.15rem;
                transition: all 0.2s ease;
            }
        
            .cc-explain-card:hover {
                border-color: var(--cc-border-strong);
        }

        .cc-explain-heading {
                font-size: 0.7rem;
            text-transform: uppercase;
                letter-spacing: 0.15em;
                font-weight: 700;
                color: var(--cc-accent-secondary);
                margin-bottom: 0.65rem;
        }

        .cc-explain-body {
                color: var(--cc-text-primary);
                font-size: 0.9rem;
                line-height: 1.6;
        }

        .cc-explain-list {
            display: grid;
                gap: 0.55rem;
                margin-top: 0.75rem;
        }

        .cc-explain-item {
            display: flex;
            justify-content: space-between;
                align-items: center;
            gap: 1rem;
                padding: 0.65rem 0.85rem;
            border-radius: 12px;
                background: var(--cc-surface);
                border: 1px solid var(--cc-border-default);
                transition: all 0.2s ease;
            }
        
            .cc-explain-item:hover {
                background: var(--cc-surface-hover);
        }

        .cc-explain-item-label {
                color: var(--cc-text-primary);
                font-size: 0.85rem;
                font-weight: 600;
        }

        .cc-explain-item-value {
                color: var(--cc-accent-primary);
                font-size: 0.9rem;
                font-weight: 800;
            white-space: nowrap;
        }

            /* ========================================
               CALLOUT ALERTS
            ======================================== */
        
        .cc-callout {
            border-radius: 18px;
                border: 2px solid var(--cc-accent-primary);
                background: var(--cc-surface);
                backdrop-filter: blur(10px);
                padding: var(--cc-space-md) var(--cc-space-lg);
                margin-bottom: var(--cc-space-md);
                box-shadow: var(--cc-shadow-sm);
                transition: all 0.2s ease;
            }
        
            .cc-callout:hover {
                box-shadow: var(--cc-shadow-md);
                transform: translateX(2px);
        }

        .cc-callout strong {
            display: block;
                color: var(--cc-text-primary);
                font-size: 1.05rem;
                margin-bottom: 0.5rem;
                font-weight: 800;
            }
        
            .cc-callout {
                color: var(--cc-text-secondary);
                line-height: 1.6;
        }

            /* ========================================
               RESPONSIVE DESIGN
            ======================================== */
        
        @media (max-width: 1100px) {
            .cc-strip,
            .cc-pick-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }

                .block-container {
                    padding-top: calc(var(--cc-top-nav-offset) + var(--cc-space-md));
                }
            
                .cc-hero {
                    padding: 1.5rem 2rem;
                }
            
                .cc-hero h1 {
                    font-size: 2.25rem;
                }
        }

        @media (max-width: 700px) {
            .cc-strip,
            .cc-pick-grid {
                grid-template-columns: 1fr;
            }

                .block-container {
                    padding-top: calc(var(--cc-top-nav-offset) + var(--cc-space-sm));
                    padding-bottom: var(--cc-space-xl);
                }
            
                .cc-hero {
                    padding: 1.25rem 1.5rem;
                    margin-top: var(--cc-space-sm);
                }
            
            .cc-hero h1 {
                    font-size: 1.85rem;
                }
            
                .cc-hero p {
                    font-size: 0.95rem;
                }
            
                .cc-panel {
                    padding: 1.25rem;
                }
            
                .cc-priority-card {
                    padding: 1rem 1.25rem;
            }

                .cc-selector-panel {
                    min-height: auto;
                }

                .cc-selector-panel .cc-panel-heading {
                    min-height: auto;
                }
        }
        
            /* ========================================
               STREAMLIT COMPONENT OVERRIDES
            ======================================== */
        
            /* Sidebar styling */
            section[data-testid="stSidebar"] {
                background: var(--cc-surface) !important;
                border-right: 1px solid var(--cc-border-default);
            }
        
            section[data-testid="stSidebar"] .block-container {
                padding-top: 2rem;
            }
        
            /* Tabs */
            .stTabs [data-baseweb="tab-list"] {
                gap: 0.5rem;
            }

            .stTabs {
                margin-top: var(--cc-space-lg);
            }

            .stTabs [data-baseweb="tab-panel"] {
                padding-top: var(--cc-space-md);
            }

            div[data-testid="stHorizontalBlock"] {
                gap: var(--cc-space-md);
            }

            div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                display: flex;
                flex-direction: column;
                gap: var(--cc-space-md);
            }

            .cc-selector-panel {
                min-height: 152px;
                display: flex;
                flex-direction: column;
                justify-content: flex-start;
            }

            .cc-selector-panel .cc-panel-heading {
                min-height: 3.3rem;
            }

            .cc-selector-panel + div[data-testid="stMultiSelect"] {
                margin-top: var(--cc-space-sm);
            }

            .cc-selector-panel + div[data-testid="stMultiSelect"] [data-baseweb="select"] {
                min-height: 48px;
            }
        
            .stTabs [data-baseweb="tab"] {
                background: var(--cc-surface);
                border: 1px solid var(--cc-border-default);
                border-radius: 12px 12px 0 0;
                color: var(--cc-text-secondary);
                font-weight: 600;
                padding: 0.75rem 1.5rem;
            }
        
            .stTabs [aria-selected="true"] {
                background: var(--cc-bg-elevated);
                border-bottom: 2px solid var(--cc-accent-primary);
                color: var(--cc-accent-primary);
            }
        
            /* Buttons */
            .stButton > button {
                background: linear-gradient(135deg, var(--cc-accent-primary), var(--cc-accent-secondary));
                color: white;
                border: none;
                border-radius: 12px;
                padding: 0.65rem 1.5rem;
                font-weight: 700;
                transition: all 0.2s ease;
            }
        
            .stButton > button:hover {
                transform: translateY(-2px);
                box-shadow: var(--cc-shadow-md);
            }
        
            /* Multiselect */
            .stMultiSelect > div > div {
                background: var(--cc-surface);
                border-color: var(--cc-border-default);
                border-radius: 12px;
            }
        
            .stMultiSelect > div > div:focus-within {
                border-color: var(--cc-accent-primary);
                box-shadow: 0 0 0 1px var(--cc-accent-primary);
            }
        
            /* Dataframes */
            .stDataFrame {
                border-radius: 16px;
                overflow: hidden;
            }
        
            /* Metrics */
            [data-testid="stMetricValue"] {
                color: var(--cc-text-primary);
                font-weight: 800;
            }
        
            [data-testid="stMetricLabel"] {
                color: var(--cc-text-muted);
                font-weight: 600;
            }
        
            /* Text inputs */
            .stTextInput > div > div > input {
                background: var(--cc-surface);
                border-color: var(--cc-border-default);
                border-radius: 12px;
                color: var(--cc-text-primary);
            }
        
            .stTextInput > div > div > input:focus {
                border-color: var(--cc-accent-primary);
                box-shadow: 0 0 0 1px var(--cc-accent-primary);
            }
        
            /* Selectbox */
            .stSelectbox > div > div {
                background: var(--cc-surface);
                border-color: var(--cc-border-default);
                border-radius: 12px;
            }
        
            /* ========================================
               ENHANCED ANIMATIONS
            ======================================== */
        
            @keyframes fadeIn {
                from {
                    opacity: 0;
                    transform: translateY(10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
        
            .cc-priority-card,
            .cc-score-row,
            .cc-panel {
                animation: fadeIn 0.4s ease-out;
            }
        
            /* Smooth transitions for theme changes */
            * {
                transition-property: background-color, border-color, color;
                transition-duration: 0.2s;
                transition-timing-function: ease;
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


def render_banned_panel(banned_heroes):
    slots = []
    max_slots = max(5, len(banned_heroes)) if banned_heroes else 5
    for slot_index in range(max_slots):
        if slot_index < len(banned_heroes):
            slot_body = (
                "<div class='cc-slot cc-slot-enemy'>"
                f"<div class='cc-slot-index'>Ban {slot_index + 1}</div>"
                f"<div class='cc-slot-hero'>{banned_heroes[slot_index]}</div>"
                "<div class='cc-slot-meta'>Removed from pick and ban recommendations</div>"
                "</div>"
            )
        else:
            slot_body = (
                "<div class='cc-slot cc-slot-enemy'>"
                f"<div class='cc-slot-index'>Ban {slot_index + 1}</div>"
                "<div class='cc-slot-empty'>No banned hero</div>"
                "</div>"
            )
        slots.append(slot_body)

    st.markdown(
        (
            "<div class='cc-panel'>"
            "<div class='cc-panel-title'>Draft State</div>"
            "<div class='cc-panel-heading'>Banned Heroes</div>"
            f"<div class='cc-pick-grid'>{''.join(slots)}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_hero_selector_panel(title, subtitle, key_prefix, options, max_selections):
    st.markdown(
        (
            "<div class='cc-panel cc-selector-panel'>"
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


def get_next_pick_recommendations(meta_df, team_df, enemy_df, selected_bans, pick_order_mode, effective_hero_pool):
    try:
        return recommend_next_picks(
            meta_df,
            team_df,
            enemy_df,
            selected_bans,
            limit=5,
            pick_order_mode=pick_order_mode,
            hero_pool=effective_hero_pool,
        )
    except TypeError:
        fallback_recommendations = recommend_next_picks(
            meta_df,
            team_df,
            enemy_df,
            selected_bans,
            limit=5,
        )
        if effective_hero_pool:
            allowed_heroes = {str(hero_name).strip() for hero_name in effective_hero_pool if str(hero_name).strip()}
            fallback_recommendations = [
                recommendation for recommendation in fallback_recommendations if recommendation.get("Hero") in allowed_heroes
            ]
        return fallback_recommendations


def get_ban_recommendations(meta_df, team_df, enemy_df, selected_bans, pick_order_mode):
    try:
        return recommend_bans(
            meta_df,
            team_df,
            enemy_df,
            selected_bans,
            limit=5,
            pick_order_mode=pick_order_mode,
        )
    except TypeError:
        return recommend_bans(
            meta_df,
            team_df,
            enemy_df,
            selected_bans,
            limit=5,
        )


def get_draft_hard_blockers(team_df):
    if team_df.empty:
        return []

    blockers = []
    team_analysis = analyze_team(team_df)
    assigned_lanes = set(team_analysis["lane_assignment"].values())
    assigned_lane_count = len(assigned_lanes)
    remaining_slots = max(0, 5 - len(team_df))
    max_reachable_lanes = assigned_lane_count + remaining_slots

    if max_reachable_lanes < len(REQUIRED_LANES):
        uncovered_lanes = [lane_name for lane_name in REQUIRED_LANES if lane_name not in assigned_lanes]
        blockers.append(
            "Lane assignment is no longer viable for a complete 5-role draft. "
            f"Current assignable lanes: {assigned_lane_count}/5, picks left: {remaining_slots}, "
            f"best-case final lanes: {max_reachable_lanes}/5. "
            f"Still uncovered: {', '.join(uncovered_lanes)}."
        )

    return blockers


def format_recommendations(recommendations, score_column):
    if not recommendations:
        return pd.DataFrame()

    formatted_df = pd.DataFrame(recommendations).copy()
    formatted_df["Why"] = formatted_df["Why"].apply(lambda reasons: "; ".join(reasons))
    formatted_df["Top Drivers"] = formatted_df["Score Drivers"].apply(
        lambda drivers: "; ".join(f"{driver['label']} {driver['value']:+.1f}" for driver in drivers[:3])
    )
    formatted_df["Projected Impact"] = formatted_df["Projected Changes"].apply(
        lambda changes: "; ".join(f"{change['label']} {change['delta']:+d}" for change in changes[:3]) if changes else "Threat-only evaluation"
    )
    ordered_columns = [
        "Hero",
        "Role",
        "Primary Lane",
        score_column,
        "True Power Score",
        "Contest Rate (%)",
        "Why",
        "Top Drivers",
        "Projected Impact",
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
        score_driver_text = " | ".join(
            f"{driver['label']} {driver['value']:+.1f}" for driver in recommendation.get("Score Drivers", [])[:3]
        )
        projected_change_text = " | ".join(
            f"{change['label']} {change['delta']:+d}" for change in recommendation.get("Projected Changes", [])[:3]
        )
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
            f"<div class='cc-priority-why'>{recommendation.get('Summary', '')}</div>"
            f"<div class='cc-priority-why'><strong>Score drivers:</strong> {score_driver_text or 'Base meta profile only'}</div>"
            f"<div class='cc-priority-why'><strong>Projected impact:</strong> {projected_change_text or 'No structural change projected'}</div>"
            f"<div class='cc-priority-why'>{'; '.join(recommendation['Why'])}</div>"
            "</div>"
        )

    st.markdown(f"<div class='cc-priority-grid'>{''.join(card_markup)}</div>", unsafe_allow_html=True)


def render_explainability_panel(title, recommendation, score_column):
    if not recommendation:
        st.info("No recommendation available to explain yet.")
        return

    score_driver_markup = "".join(
        (
            "<div class='cc-explain-item'>"
            f"<div class='cc-explain-item-label'>{driver['label']}</div>"
            f"<div class='cc-explain-item-value'>{driver['value']:+.1f}</div>"
            "</div>"
        )
        for driver in recommendation.get("Score Drivers", [])[:4]
    )
    projected_change_markup = "".join(
        (
            "<div class='cc-explain-item'>"
            f"<div class='cc-explain-item-label'>{change['label']}</div>"
            f"<div class='cc-explain-item-value'>{change['delta']:+d}</div>"
            "</div>"
        )
        for change in recommendation.get("Projected Changes", [])[:4]
    )
    reason_text = "; ".join(recommendation.get("Why", []))

    st.markdown(
        (
            "<div class='cc-panel'>"
            f"<div class='cc-panel-title'>{title}</div>"
            f"<div class='cc-panel-heading'>{recommendation['Hero']} ({recommendation[score_column]:.1f})</div>"
            f"<div class='cc-score-detail'>{recommendation.get('Summary', '')}</div>"
            "<div class='cc-explain-stack'>"
            "<div class='cc-explain-card'>"
            "<div class='cc-explain-heading'>Primary Reasons</div>"
            f"<div class='cc-explain-body'>{reason_text or 'No additional reasons recorded.'}</div>"
            "</div>"
            "<div class='cc-explain-card'>"
            "<div class='cc-explain-heading'>Score Drivers</div>"
            f"<div class='cc-explain-list'>{score_driver_markup or '<div class=\'cc-explain-body\'>No score drivers recorded.</div>'}</div>"
            "</div>"
            "<div class='cc-explain-card'>"
            "<div class='cc-explain-heading'>Projected Team Impact</div>"
            f"<div class='cc-explain-list'>{projected_change_markup or '<div class=\'cc-explain-body\'>This recommendation is driven by threat evaluation rather than a projected team change.</div>'}</div>"
            "</div>"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_quick_calls(team_analysis, next_pick_recommendations, ban_recommendations):
    priority_pick = next_pick_recommendations[0]["Hero"] if next_pick_recommendations else "No pick available"
    priority_ban = ban_recommendations[0]["Hero"] if ban_recommendations else "No ban target available"
    open_lanes = ", ".join(team_analysis["missing_lanes"]) if team_analysis["missing_lanes"] else "No open lanes"
    pick_summary = next_pick_recommendations[0].get("Summary", "") if next_pick_recommendations else ""
    ban_summary = ban_recommendations[0].get("Summary", "") if ban_recommendations else ""

    st.markdown(
        (
            "<div class='cc-callout'>"
            f"<strong>Pick now: {priority_pick}</strong>"
            f"{pick_summary or 'Best immediate value based on your current structural gaps and meta power.'} Open lanes: {open_lanes}."
            "</div>"
            "<div class='cc-callout'>"
            f"<strong>Ban now: {priority_ban}</strong>"
            f"{ban_summary or 'Highest-pressure removal based on meta threat, flexibility, and how exposed your current draft is.'}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_best_next_action(team_analysis, next_pick_recommendations, ban_recommendations):
    if not next_pick_recommendations and not ban_recommendations:
        st.info("No immediate action available.")
        return

    has_critical_issue = any(issue["severity"] == "error" for issue in team_analysis.get("issues", []))
    should_force_pick = bool(team_analysis.get("missing_lanes")) or team_analysis.get("frontline_count", 0) == 0

    selected_action = "pick"
    if not next_pick_recommendations:
        selected_action = "ban"
    elif not ban_recommendations:
        selected_action = "pick"
    elif not has_critical_issue and not should_force_pick:
        pick_score = next_pick_recommendations[0]["Recommendation Score"]
        ban_score = ban_recommendations[0]["Threat Score"]
        if ban_score > (pick_score * 1.1):
            selected_action = "ban"

    if selected_action == "pick":
        hero_name = next_pick_recommendations[0]["Hero"]
        st.markdown(
            (
                "<div class='cc-callout'>"
                f"<strong>Best Next Action: PICK {hero_name}</strong>"
                "Use this as your immediate lock to maximize current draft value."
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        if st.button(f"Apply Pick: {hero_name}", key="apply_best_pick"):
            locked_team = list(st.session_state.get("friendly_draft_selector", []))
            if hero_name not in locked_team and len(locked_team) < 5:
                locked_team.append(hero_name)
                st.session_state["friendly_draft_selector"] = locked_team
                st.rerun()
    else:
        hero_name = ban_recommendations[0]["Hero"]
        st.markdown(
            (
                "<div class='cc-callout'>"
                f"<strong>Best Next Action: BAN {hero_name}</strong>"
                "Remove this threat now to reduce enemy draft pressure."
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        if st.button(f"Apply Ban: {hero_name}", key="apply_best_ban"):
            banned_heroes = list(st.session_state.get("banned_draft_selector", []))
            if hero_name not in banned_heroes and len(banned_heroes) < 10:
                banned_heroes.append(hero_name)
                st.session_state["banned_draft_selector"] = banned_heroes
                st.rerun()


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
        sync_ready = bool(approved_endpoint)
        if sync_ready:
            st.caption(f"Approved endpoint: {approved_endpoint}")
            if st.button("Sync Approved Data Source"):
                with st.spinner("Synchronizing with approved source..."):
                    raw_data = get_mlbb_meta_api()
                    if raw_data.empty:
                        st.error("Synchronization failed. Check the endpoint or authorization if required.")
                    else:
                        analyzed_meta = analyze_meta(raw_data)
                        analyzed_meta.to_csv(DATA_FILE, index=False)
                        st.cache_data.clear()
                        st.success("Synchronization successful. Local database updated.")
                        st.rerun()
        else:
            st.warning(
                f"Synchronization is disabled until {API_ENDPOINT_ENV} is configured."
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
st.sidebar.markdown("### Ranked Optimization")
pick_order_mode = st.sidebar.selectbox(
    "Pick-Order Mode",
    ["Balanced", "Early Priority", "Mid Draft", "Last Pick"],
    index=0,
)
restrict_to_hero_pool = st.sidebar.checkbox("Restrict picks to my hero pool", value=False)
selected_hero_pool = st.sidebar.multiselect(
    "My Hero Pool",
    options=hero_list,
    default=[],
    max_selections=40,
)
effective_hero_pool = selected_hero_pool if (restrict_to_hero_pool and selected_hero_pool) else None

st.sidebar.divider()
st.sidebar.markdown("### Most Contested Heroes")
for _, row in meta_df.nlargest(5, "Contest Rate (%)").iterrows():
    st.sidebar.markdown(f"**{row['Hero']}** ({row['Contest Rate (%)']:.2f}%)")

handle_admin_actions(hero_list, load_lane_database())

st.markdown("## Draft Command Center")
draft_col, enemy_col, banned_col = st.columns(3)
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
with banned_col:
    selected_bans = render_hero_selector_panel(
        "Banned Heroes",
        "Heroes removed from draft consideration.",
        "banned",
        hero_list,
        10,
    )

overlap = sorted(set(selected_team).intersection(selected_enemy))
if overlap:
    st.error("A hero cannot be locked on both sides. Remove duplicates: " + ", ".join(overlap))
    st.stop()

banned_conflicts = sorted((set(selected_team) | set(selected_enemy)).intersection(selected_bans))
if banned_conflicts:
    st.error("A hero cannot be both banned and locked in draft. Remove duplicates: " + ", ".join(banned_conflicts))
    st.stop()

team_df = build_selection_df(meta_df, selected_team)
enemy_df = build_selection_df(meta_df, selected_enemy)
draft_hard_blockers = get_draft_hard_blockers(team_df)

if draft_hard_blockers:
    st.error("Draft validation blocked: adjust your locked heroes before continuing.")
    for blocker_message in draft_hard_blockers:
        st.warning(blocker_message)

team_display_col, enemy_display_col, banned_display_col = st.columns(3)
with team_display_col:
    render_pick_panel("Your Locked Heroes", team_df, "friendly")
with enemy_display_col:
    render_pick_panel("Enemy Locked Heroes", enemy_df, "enemy")
with banned_display_col:
    render_banned_panel(selected_bans)

command_tab, breakdown_tab, explorer_tab = st.tabs([
    "Command Board",
    "Draft Breakdown",
    "Meta Explorer",
])

if selected_team and not draft_hard_blockers:
    team_analysis = analyze_team(team_df)
    next_pick_recommendations = get_next_pick_recommendations(
        meta_df,
        team_df,
        enemy_df,
        selected_bans,
        pick_order_mode,
        effective_hero_pool,
    )
    ban_recommendations = get_ban_recommendations(
        meta_df,
        team_df,
        enemy_df,
        selected_bans,
        pick_order_mode,
    )

    if restrict_to_hero_pool and not selected_hero_pool:
        st.warning("Hero pool lock is enabled but your hero pool is empty. Add heroes in the sidebar to unlock pick recommendations.")

    render_score_cards(team_analysis, len(selected_team))

    with command_tab:
        quick_col, score_col, lane_col = st.columns([1.1, 1.15, 0.95])
        with quick_col:
            render_quick_calls(team_analysis, next_pick_recommendations, ban_recommendations)
            render_best_next_action(team_analysis, next_pick_recommendations, ban_recommendations)
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
        risk_col, pick_table_col, ban_table_col, explain_col = st.columns([0.85, 1.05, 1.05, 1.05])
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
        with explain_col:
            render_explainability_panel(
                "Pick Explanation",
                next_pick_recommendations[0] if next_pick_recommendations else None,
                "Recommendation Score",
            )
            render_explainability_panel(
                "Ban Explanation",
                ban_recommendations[0] if ban_recommendations else None,
                "Threat Score",
            )
else:
    with command_tab:
        if draft_hard_blockers:
            st.error("Draft is currently blocked by lane viability checks. Update your locked heroes to continue.")
        else:
            st.info("Start by locking your own heroes to generate draft analysis, next-pick suggestions, and ban targets.")
    with breakdown_tab:
        if draft_hard_blockers:
            st.info("Detailed breakdown is disabled until your draft passes hard validation.")
        else:
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
