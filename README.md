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
- **Draft Command Center:** Lock your team and the enemy team separately, then get a structured draft score, lane plan, risk report, next-pick recommendations, and ban targets.
- **Tactical Filters:** Quickly filter by role, lane, or hero name to inspect the active meta table.
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

### Environment Variables
The admin sync flow now reads credentials and access controls from environment variables instead of hardcoded values:

```powershell
$env:MLBB_ADMIN_PASSWORD="your-admin-password"
$env:MLBB_META_API_URL="https://api.gms.moontontech.com/api/gms/source/2669606/2756569"
$env:MLBB_API_AUTHORIZATION="your-api-authorization-token"
```

If these values are not configured, the dashboard still works in read-only mode against the local CSV, but admin sync is disabled.

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

### Run Tests
Run the draft engine test suite with:
```bash
python -m unittest discover -s tests -p "test_*.py"
```

## 🎯 Key Features
- **Structured Draft Analysis:** Lane coverage, frontline, damage mix, scaling, and overall draft score.
- **Recommendation Engine:** Best next picks and high-priority ban suggestions based on current locks.
- **Explainable Recommendations:** Pick and ban suggestions now show score drivers and projected team impact instead of opaque ranking alone.
- **Threat Level Visualization:** Progress bars for Contest Rates and color-coded Win Rate metrics.
- **Admin Sync Controls:** A built-in Admin panel for synchronizing the approved API source and managing lane mappings.
- **Hidden OP Finder:** Identify low-visibility heroes that are currently dominating the high-rank win rates.

## 🛡️ Security Note
The dashboard no longer ships with embedded admin or API credentials. Keep `MLBB_ADMIN_PASSWORD` and `MLBB_API_AUTHORIZATION` out of source control, and only point `MLBB_META_API_URL` at approved HTTPS endpoints.

---
*Disclaimer: This tool is for educational and tactical analysis only. Data is sourced from public API endpoints.*
