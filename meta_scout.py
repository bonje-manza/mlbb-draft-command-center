import os
from urllib.parse import urlparse

import pandas as pd
import requests

DEFAULT_ENDPOINT = "https://api.gms.moontontech.com/api/gms/source/2669606/2756568"
APPROVED_HOSTS = {"api.gms.moontontech.com", "www.mobilelegends.com", "mobilelegends.com"}
REQUIRED_API_TOKEN_ENV = "MLBB_API_AUTHORIZATION"
API_ENDPOINT_ENV = "MLBB_META_API_URL"


def _resolve_endpoint(endpoint=None):
    resolved_endpoint = endpoint or os.getenv(API_ENDPOINT_ENV, DEFAULT_ENDPOINT)
    parsed_endpoint = urlparse(resolved_endpoint)

    if parsed_endpoint.scheme != "https":
        raise ValueError("Meta endpoint must use HTTPS.")

    hostname = parsed_endpoint.netloc.lower()
    if hostname not in APPROVED_HOSTS:
        raise ValueError("Meta endpoint host is not approved.")

    return resolved_endpoint


def _build_headers(authorization_token=None):
    resolved_token = authorization_token or os.getenv(REQUIRED_API_TOKEN_ENV)
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json;charset=UTF-8",
        "origin": "https://www.mobilelegends.com",
        "referer": "https://www.mobilelegends.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    }

    if resolved_token:
        headers["authorization"] = resolved_token

    return headers


def get_mlbb_meta_api(endpoint=None, authorization_token=None):
    print("Initiating data retrieval...")

    try:
        resolved_endpoint = _resolve_endpoint(endpoint)
        headers = _build_headers(authorization_token)
        if "authorization" not in headers:
            print(
                f"No API token detected ({REQUIRED_API_TOKEN_ENV} not set). Attempting unauthenticated request..."
            )
    except ValueError as exc:
        print(f"Configuration Error: {exc}")
        return pd.DataFrame()

    json_data = {
        'pageSize': 200,
        'pageIndex': 1,
        'filters': [
            {'field': 'bigrank', 'operator': 'eq', 'value': '9'},
            {'field': 'match_type', 'operator': 'eq', 'value': 0},
        ],
        'sorts': [
            {'data': {'field': 'main_hero_win_rate', 'order': 'desc'}, 'type': 'sequence'}
        ],
        'fields': [
            'main_hero',
            'main_hero_appearance_rate',
            'main_hero_ban_rate',
            'main_hero_win_rate'
        ],
    }

    try:
        response = requests.post(resolved_endpoint, headers=headers, json=json_data, timeout=30)
        if response.status_code in {401, 403}:
            print(
                "Authorization failed. This endpoint currently requires a valid authorization header from an authenticated browser session."
            )
            print(
                f"Set {REQUIRED_API_TOKEN_ENV} with the intercepted request token and try again."
            )
            return pd.DataFrame()

        response.raise_for_status() 
        
        data = response.json()
        print(f"Data successfully retrieved from {resolved_endpoint}.")
        
        # --- RECURSIVE SEARCH ALGORITHM ---
        lists_found = []
        def search_for_lists(obj):
            if isinstance(obj, list):
                lists_found.append(obj)
            elif isinstance(obj, dict):
                for value in obj.values():
                    search_for_lists(value)
                    
        search_for_lists(data)
        valid_lists = [l for l in lists_found if len(l) > 0 and isinstance(l[0], dict)]
        
        if not valid_lists:
            print("Error: No hero data structure found in the response.")
            return pd.DataFrame()
            
        hero_list = max(valid_lists, key=len)
        print(f"Dataset identified. Extracted {len(hero_list)} hero entries.")
        
        # --- DATA EXTRACTION ---
        heroes_data = []
        for hero in hero_list:
            core_data = hero.get('data', hero) if isinstance(hero.get('data'), dict) else hero
            
            name_obj = core_data.get('main_hero', 'Unknown')
            if isinstance(name_obj, dict):
                name = str(name_obj.get('data', {}).get('name', 'Unknown')).strip()
            else:
                name = str(name_obj).strip()
            
            win_rate = float(core_data.get('main_hero_win_rate', 0.0) or 0.0)
            pick_rate = float(core_data.get('main_hero_appearance_rate', 0.0) or 0.0)
            ban_rate = float(core_data.get('main_hero_ban_rate', 0.0) or 0.0)
            
            if win_rate <= 1.0 and win_rate > 0:
                win_rate *= 100
                pick_rate *= 100
                ban_rate *= 100
            
            heroes_data.append({
                "Hero": name,
                "Win Rate": round(win_rate, 2),
                "Pick Rate": round(pick_rate, 2),
                "Ban Rate": round(ban_rate, 2)
            })
            
        extracted_df = pd.DataFrame(heroes_data)
        if extracted_df.empty:
            return extracted_df

        extracted_df['Hero'] = extracted_df['Hero'].astype(str).str.strip()
        extracted_df = extracted_df[extracted_df['Hero'] != '']
        extracted_df = extracted_df.drop_duplicates(subset=['Hero'], keep='first')
        for column_name in ['Win Rate', 'Pick Rate', 'Ban Rate']:
            extracted_df[column_name] = pd.to_numeric(extracted_df[column_name], errors='coerce').fillna(0.0).round(2)

        return extracted_df.reset_index(drop=True)

    except Exception as e:
        print(f"System Error: {e}")
        return pd.DataFrame()


def analyze_meta(df):
    if df.empty:
        print("No data available for analysis.")
        return df

    required_columns = {'Hero', 'Win Rate', 'Pick Rate', 'Ban Rate'}
    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        print(f"Missing required columns for analysis: {', '.join(sorted(missing_columns))}")
        return pd.DataFrame()
        
    print(f"Performing meta-analysis on {len(df)} hero profiles...")

    df = df.copy()
    df['Hero'] = df['Hero'].astype(str).str.strip()
    df = df[df['Hero'] != '']
    df = df.drop_duplicates(subset=['Hero'], keep='first')
    for column_name in ['Win Rate', 'Pick Rate', 'Ban Rate']:
        df[column_name] = pd.to_numeric(df[column_name], errors='coerce').fillna(0.0)
    
    df['Contest Rate (%)'] = (df['Ban Rate'] + df['Pick Rate']).round(2)
    df['True Match Presence (%)'] = (df['Pick Rate'] * 10).round(2)
    
    # --- TRUE POWER ALGORITHM V2 ---
    fear_index = (df['Ban Rate'] * 0.6) + (df['Pick Rate'] * 0.25)
    wr_delta = df['Win Rate'] - 50.0
    performance_score = wr_delta * (4.0 + (df['Pick Rate'] * 0.1))
    
    df['True Power Score'] = (fear_index + performance_score).round(1)
    
    def assign_tier(row):
        if row['Ban Rate'] >= 35.0 or (row['Contest Rate (%)'] >= 50.0 and row['Win Rate'] >= 50.0):
            return "S-Tier (Absolute Meta / Must Ban)"
        elif row['Pick Rate'] >= 1.5 and row['Win Rate'] < 47.5:
            return "Solo-Queue Trap (Avoid at all costs)"
        elif row['Contest Rate (%)'] >= 20.0 or (row['Pick Rate'] >= 1.5 and row['Win Rate'] >= 50.5):
            return "A-Tier (Comfort Staple)"
        elif row['Pick Rate'] < 1.0 and row['Ban Rate'] < 10.0 and row['Win Rate'] >= 52.5:
            return "Hidden OP (The Specialist)"
        elif row['Win Rate'] >= 50.0:
            return "B-Tier (Reliable / Strong)"
        elif row['Win Rate'] >= 47.5:
            return "C-Tier (Situational / Average)"
        else:
            return "D-Tier (Out of Meta / Weak)"

    df['Meta Tier'] = df.apply(assign_tier, axis=1)
    df = df.sort_values(by='True Power Score', ascending=False).reset_index(drop=True)
    df.insert(0, 'True Overall Rank', range(1, len(df) + 1))
    
    df = df[['True Overall Rank', 'Hero', 'Meta Tier', 'True Power Score', 'Contest Rate (%)', 'Ban Rate', 'Pick Rate', 'Win Rate', 'True Match Presence (%)']]
    
    return df

def export_to_excel(df):
    if df.empty:
        return
        
    print("\nGenerating tactical spreadsheet...")
    file_name = "MLBB_Meta_Tiers.xlsx"
    
    tier_colors = {
        "S-Tier": "FF0000",          
        "A-Tier": "00FF00",          
        "Hidden OP": "800080",       
        "Solo-Queue Trap": "FFA500", 
        "B-Tier": "808080"           
    }
    
    with pd.ExcelWriter(file_name, engine='openpyxl') as writer:
        df_all = df.copy()
        df_all.insert(0, 'Overall Rank', range(1, len(df_all) + 1))
        df_all.to_excel(writer, sheet_name="All Heroes", index=False)
        
        ws_all = writer.sheets["All Heroes"]
        ws_all.sheet_properties.tabColor = "000000" 
        for column_cells in ws_all.columns:
            length = max(len(str(cell.value)) for cell in column_cells)
            ws_all.column_dimensions[column_cells[0].column_letter].width = length + 2

        grouped_meta = df.groupby('Meta Tier')
        for tier_name, tier_data in grouped_meta:
            clean_tab_name = tier_name.split(' (')[0].strip()
            clean_df = tier_data.drop(columns=['Meta Tier'])
            clean_df.to_excel(writer, sheet_name=clean_tab_name, index=False)
            ws = writer.sheets[clean_tab_name]
            if clean_tab_name in tier_colors:
                ws.sheet_properties.tabColor = tier_colors[clean_tab_name]
            for column_cells in ws.columns:
                length = max(len(str(cell.value)) for cell in column_cells)
                ws.column_dimensions[column_cells[0].column_letter].width = length + 2
                
    print(f"Export complete. File saved as '{file_name}'.")

if __name__ == "__main__":
    raw_data = get_mlbb_meta_api()
    analyzed_meta = analyze_meta(raw_data)
    
    if not analyzed_meta.empty:
        analyzed_meta.to_csv("current_mlbb_meta_api.csv", index=False)
        export_to_excel(analyzed_meta)
