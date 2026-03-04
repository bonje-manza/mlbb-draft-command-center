import requests
import pandas as pd

def get_mlbb_meta_api():
    print("Executing the cURL Heist...")

    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9',
        'authorization': 'DTQW9B4FuLk0JaVBl1PBK4TWung=',
        'content-type': 'application/json;charset=UTF-8',
        'origin': 'https://www.mobilelegends.com',
        'priority': 'u=1, i',
        'referer': 'https://www.mobilelegends.com/',
        'sec-ch-ua': '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
        'x-actid': '2669607',
        'x-appid': '2669606',
        'x-lang': 'en',
    }

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
        response = requests.post('https://api.gms.moontontech.com/api/gms/source/2669606/2756569', headers=headers, json=json_data)
        response.raise_for_status() 
        
        data = response.json()
        print("Infiltration successful! JSON payload secured.")
        
        # --- THE RESTORED RECURSIVE SEARCH ALGORITHM ---
        # This completely ignores Moonton's folder names and just finds the largest list in the payload.
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
            print("CRITICAL ERROR: No hero data structure found in the JSON.")
            return pd.DataFrame()
            
        hero_list = max(valid_lists, key=len)
        print(f"Data folder located! Extracted {len(hero_list)} heroes.")
        
        # --- ROBUST DATA EXTRACTION ---
        heroes_data = []
        for hero in hero_list:
            # Moonton randomly shifts between wrapping stats in a 'data' folder or keeping them exposed.
            # This safely handles both.
            core_data = hero.get('data', hero) if isinstance(hero.get('data'), dict) else hero
            
            # Safely extract the name, whether it's nested in another dictionary or just a raw string
            name_obj = core_data.get('main_hero', 'Unknown')
            if isinstance(name_obj, dict):
                name = str(name_obj.get('data', {}).get('name', 'Unknown')).strip()
            else:
                name = str(name_obj).strip()
            
            # Extract decimals and format them to percentages
            win_rate = float(core_data.get('main_hero_win_rate', 0.0) or 0.0)
            pick_rate = float(core_data.get('main_hero_appearance_rate', 0.0) or 0.0)
            ban_rate = float(core_data.get('main_hero_ban_rate', 0.0) or 0.0)
            
            # Safeguard: Multiply by 100 only if Moonton is sending raw decimals (e.g. 0.54 instead of 54.0)
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
            
        return pd.DataFrame(heroes_data)

    except Exception as e:
        print(f"Execution Error: {e}")
        return pd.DataFrame()
        
# ... (Keep your analyze_meta and export_to_excel functions exactly as they are down here!) ...


def analyze_meta(df):
    if df.empty:
        print("No data to analyze.")
        return df
        
    print(f"Applying macro-analysis to {len(df)} heroes...")
    
    df['Contest Rate (%)'] = df['Ban Rate'] + df['Pick Rate']
    df['True Match Presence (%)'] = df['Pick Rate'] * 10
    
    # --- THE TRUE POWER ALGORITHM V2 (WEIGHTED EFFICACY) ---
    # 1. The Fear Index: Bans indicate undeniable meta threat, weighted heavier than Picks.
    fear_index = (df['Ban Rate'] * 0.6) + (df['Pick Rate'] * 0.25)
    
    # 2. Performance Delta: How far from the 50% baseline is the hero?
    wr_delta = df['Win Rate'] - 50.0
    
    # 3. Efficacy Multiplier: Scales the win rate impact based on sample size (Pick Rate).
    # High pick + high WR = Massive boost. High pick + low WR = Catastrophic penalty.
    performance_score = wr_delta * (4.0 + (df['Pick Rate'] * 0.1))
    
    # Calculate the final composite score
    df['True Power Score'] = round(fear_index + performance_score, 1)
    
    def assign_tier(row):
        # S-Tier: The Permabans OR heavily contested winners
        if row['Ban Rate'] >= 35.0 or (row['Contest Rate (%)'] >= 50.0 and row['Win Rate'] >= 50.0):
            return "S-Tier (Absolute Meta / Must Ban)"
        
        # Solo-Queue Trap: High presence (>=15% of matches) but actively dragging the team down
        elif row['Pick Rate'] >= 1.5 and row['Win Rate'] < 47.5:
            return "Solo-Queue Trap (Avoid at all costs)"
            
        # A-Tier: High contestation OR solid presence with a positive win rate
        # Checked BEFORE Hidden OP so heavily contested heroes don't slip through
        elif row['Contest Rate (%)'] >= 20.0 or (row['Pick Rate'] >= 1.5 and row['Win Rate'] >= 50.5):
            return "A-Tier (Comfort Staple)"
            
        # Hidden OP: Low pick rate, low ban rate, but mathematically dominant when played
        elif row['Pick Rate'] < 1.0 and row['Ban Rate'] < 10.0 and row['Win Rate'] >= 52.5:
            return "Hidden OP (The Specialist)"
            
        # B-Tier: Above average baseline, reliable
        elif row['Win Rate'] >= 50.0:
            return "B-Tier (Reliable / Strong)"
            
        # C-Tier: Below average, highly situational
        elif row['Win Rate'] >= 47.5:
            return "C-Tier (Situational / Average)"
            
        # D-Tier: The bottom of the barrel
        else:
            return "D-Tier (Out of Meta / Weak)"

    df['Meta Tier'] = df.apply(assign_tier, axis=1)
    
    # SORT BY THE NEW TRUE POWER SCORE
    df = df.sort_values(by='True Power Score', ascending=False).reset_index(drop=True)
    
    # ASSIGN THE TRUE OVERALL RANK
    df.insert(0, 'True Overall Rank', range(1, len(df) + 1))
    
    # Reorder columns to showcase the new metrics
    df = df[['True Overall Rank', 'Hero', 'Meta Tier', 'True Power Score', 'Contest Rate (%)', 'Ban Rate', 'Pick Rate', 'Win Rate', 'True Match Presence (%)']]
    
    return df

def export_to_excel(df):
    if df.empty:
        return
        
    print("\nDrafting tactical spreadsheet with color-coded intel...")
    file_name = "MLBB_Meta_Tiers.xlsx"
    
    tier_colors = {
        "S-Tier": "FF0000",          
        "A-Tier": "00FF00",          
        "Hidden OP": "800080",       
        "Solo-Queue Trap": "FFA500", 
        "B-Tier": "808080"           
    }
    
    with pd.ExcelWriter(file_name, engine='openpyxl') as writer:
        
        # --- NEW: The "All Heroes" Master Ranking Sheet ---
        # Create a copy so we don't accidentally alter the main DataFrame
        df_all = df.copy()
        
        # Insert the 'Overall Rank' column at the very front (Index 0)
        df_all.insert(0, 'Overall Rank', range(1, len(df_all) + 1))
        
        # Write it to the first sheet
        df_all.to_excel(writer, sheet_name="All Heroes", index=False)
        
        # Format the master sheet
        ws_all = writer.sheets["All Heroes"]
        ws_all.sheet_properties.tabColor = "000000" # Black tab color for the master sheet
        for column_cells in ws_all.columns:
            length = max(len(str(cell.value)) for cell in column_cells)
            ws_all.column_dimensions[column_cells[0].column_letter].width = length + 2

        # --- EXISTING: The Individual Tier Sheets ---
        grouped_meta = df.groupby('Meta Tier')
        
        for tier_name, tier_data in grouped_meta:
            clean_tab_name = tier_name.split(' (')[0].strip()
            # We remove the Meta Tier column here because the whole sheet is just that tier
            clean_df = tier_data.drop(columns=['Meta Tier'])
            
            clean_df.to_excel(writer, sheet_name=clean_tab_name, index=False)
            
            ws = writer.sheets[clean_tab_name]
            
            if clean_tab_name in tier_colors:
                ws.sheet_properties.tabColor = tier_colors[clean_tab_name]
            
            # AUTO-FORMATTING: Adjusting column widths automatically
            for column_cells in ws.columns:
                length = max(len(str(cell.value)) for cell in column_cells)
                ws.column_dimensions[column_cells[0].column_letter].width = length + 2
                
    print(f"Spreadsheet secured! Open '{file_name}' to view your optimized drafting dashboard.")

if __name__ == "__main__":
    raw_data = get_mlbb_meta_api()
    analyzed_meta = analyze_meta(raw_data)
    
    if not analyzed_meta.empty:
        # Save the master raw CSV (Optional, but good for backups)
        analyzed_meta.to_csv("current_mlbb_meta_api.csv", index=False)
        
        # Trigger the new Excel grouping function
        export_to_excel(analyzed_meta)