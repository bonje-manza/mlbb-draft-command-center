# 🏆 MLBB Meta Analyzer: Immortal Command Center

A tactical intelligence suite for **Mobile Legends: Bang Bang (MLBB)**, designed to provide Mythical Glory+ players with mathematical drafting advantages. This project transforms raw Moonton API data into actionable insights through a weighted power algorithm and a live synergy analyzer.

## 🛠️ Project Architecture

The system is split into a data-gathering "Scout" engine and an interactive "Command Center" dashboard:

### 1. `meta_scout.py` (The Intelligence Engine)
The backend "Scout" performs what we call the **cURL Heist**—intercepting and parsing real-time meta data from the official Moonton API. 
- **The True Power Algorithm:** Instead of looking at win rates alone, it calculates a `True Power Score` by weighting **Ban Rate** (fear index), **Pick Rate** (reliability), and **Win Rate** (efficacy).
- **Automated Categorization:** Heroes are automatically sorted into tiers like *S-Tier (Must Ban)*, *Hidden OP (Low pick/High win)*, and the dreaded *Solo-Queue Trap*.
- **Exports:** Generates `current_mlbb_meta_api.csv` for the dashboard and a color-coded `MLBB_Meta_Tiers.xlsx` for deep-dive analysis.

### 2. `dashboard.py` (The Command Center)
A high-performance **Streamlit** application that serves as your tactical drafting interface.
- **Live Team Synergy Analyzer:** As you select heroes, it dynamically checks your squad for critical weaknesses like "No Frontline," "Too Much Magic Damage," or "No Late-Game Carry."
- **Tactical Filters:** Quickly filter by role (Assassin, Tank, etc.) or search for specific heroes to see their current meta standing.
- **Performance Optimized:** Utilizes Streamlit caching to ensure fluid interactions even when processing large datasets.

### 3. Data Assets
- `hero_roles.json`: The source of truth for hero-to-role mapping.
- `MLBB_Meta_Tiers.xlsx`: A spreadsheet with color-coded tabs for different meta tiers.
- `current_mlbb_meta_api.csv`: The processed dataset powering the live dashboard.

## 🚀 Getting Started

### Prerequisites
Ensure you have Python 3.9+ installed and all dependencies:
```bash
pip install -r requirements.txt
```

### Step 1: Execute the Data Infiltration
Before running the dashboard, you need to pull the latest meta data:
```bash
python meta_scout.py
```
This will fetch the data, apply the power algorithm, and generate your local database files.

### Step 2: Launch the Command Center
Start the interactive dashboard:
```bash
streamlit run dashboard.py
```

## 🎯 Key Features
- **Synergy Validation:** Real-time feedback on team composition balance.
- **Threat Level Visualization:** Progress bars for Contest Rates and color-coded Win Rate metrics.
- **Admin Patching:** A built-in Admin panel to update the API endpoint directly if the data feed shifts.
- **Hidden OP Finder:** Identify low-visibility heroes that are currently dominating the high-rank win rates.

## 🛡️ Security Note
The dashboard includes an **Admin Override** panel. The default access passcode is stored in `dashboard.py`. Ensure this is updated or moved to environment variables before deploying to a public server.

---
*Disclaimer: This tool is for educational and tactical analysis only. Data is sourced from public API endpoints.*
