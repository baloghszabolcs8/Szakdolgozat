import pandas as pd
import os
import random

def load_database():
    aktualis_mappa = os.path.dirname(os.path.abspath(__file__))
    fajl_utvonal = os.path.join(aktualis_mappa, 'adatok.xlsx')
    
    print("Adatbázis betöltése")
    try:
        df = pd.read_excel(fajl_utvonal, engine='openpyxl', header=15)
        
        df.columns = [str(c).strip() for c in df.columns]

        if 'Exercise' not in df.columns:
            for col in df.columns:
                if 'exercise' in col.lower():
                    df.rename(columns={col: 'Exercise'}, inplace=True)
                    break

        df = df.dropna(subset=['Exercise'])

        fontos_oszlopok = [
            'Difficulty Level', 
            'Target Muscle Group', 
            'Prime Mover Muscle', 
            'Secondary Muscle', 
            'Tertiary Muscle', 
            'Primary Equipment', 
            'Short YouTube Demonstration'
        ]
        
        for col in fontos_oszlopok:
            if col in df.columns:
                df[col] = df[col].astype(str)

        if 'Short YouTube Demonstration' in df.columns:
            try:
                from openpyxl import load_workbook
                wb = load_workbook(fajl_utvonal, data_only=False)
                ws = wb.active 

                video_col_index = None
                header_row = 16 
                for cell in ws[header_row]:
                    if cell.value and 'Short YouTube Demonstration' in str(cell.value).strip():
                        video_col_index = cell.column
                        break
                
                if video_col_index:
                    count = 0
                    for index, row in df.iterrows():
                        excel_row = index + 17 
                        cell = ws.cell(row=excel_row, column=video_col_index)
                        
                        if cell.hyperlink and cell.hyperlink.target:
                            df.at[index, 'Short YouTube Demonstration'] = cell.hyperlink.target
                            count += 1
                    print(f"Siker! {count} db rejtett link")
            except Exception as e:
                print(f"Hiba a linkek kinyerése közben{e}")

        print(f"{len(df)} gyakorlat betöltve.")
        return df

    except Exception as e:
        print(f"Kritikus hiba az Excel betöltésekor: {e}")
        return None

def get_muscle_regex(slot_name):
    if slot_name == 'Legs': return 'Quadriceps|Hamstrings|Glutes|Calves|Legs'
    if slot_name == 'Push': return 'Chest|Shoulders|Triceps'
    if slot_name == 'Pull': return 'Back|Biceps|Lats'
    if slot_name == 'Core': return 'Abdominals|Lower Back|Core'
    if slot_name == 'Arms': return 'Biceps|Triceps|Forearms'
    if slot_name == 'Full Body': return 'Full Body|Cardio'
    return slot_name 

def find_best_exercise(df, slot_name, difficulty, style, used_exercises, worked_muscles):
    muscle_regex = get_muscle_regex(slot_name)

    if 'Target Muscle Group' not in df.columns:
        return None, "Hiányzó oszlopok"

    mask_primary = df['Target Muscle Group'].str.contains(muscle_regex, case=False, na=False)
    
    mask_prime = False
    if 'Prime Mover Muscle' in df.columns:
        mask_prime = df['Prime Mover Muscle'].str.contains(muscle_regex, case=False, na=False)

    mask_secondary = False
    if 'Secondary Muscle' in df.columns:
        mask_secondary = df['Secondary Muscle'].str.contains(muscle_regex, case=False, na=False)

    mask_tertiary = False
    if 'Tertiary Muscle' in df.columns:
        mask_tertiary = df['Tertiary Muscle'].str.contains(muscle_regex, case=False, na=False)

    total_muscle_mask = mask_primary | mask_prime | mask_secondary | mask_tertiary
    
    if 'Difficulty Level' in df.columns:
        mask_difficulty = df['Difficulty Level'].str.contains(difficulty, case=False, na=False)
    else:
        mask_difficulty = True

    pool = df[total_muscle_mask & mask_difficulty]
    
    final_pool = pd.DataFrame()
    match_type = "Nincs találat"

    if style:
        style_pool = pool[
            pool.apply(lambda row: row.astype(str).str.contains(style, case=False).any(), axis=1)
        ]
        if not style_pool.empty and 'Exercise' in style_pool.columns:
            unused = style_pool[~style_pool['Exercise'].isin(used_exercises)]
            if len(unused) > 0:
                final_pool = unused
                match_type = "Tökéletes"

    if final_pool.empty and not pool.empty and 'Exercise' in pool.columns:
        unused_strict = pool[~pool['Exercise'].isin(used_exercises)]
        if len(unused_strict) > 0:
            final_pool = unused_strict
            match_type = "Alternatíva"
    
    if final_pool.empty:
        pool_basic = df[total_muscle_mask]
        if not pool_basic.empty and 'Exercise' in pool_basic.columns:
            unused_basic = pool_basic[~pool_basic['Exercise'].isin(used_exercises)]
            if len(unused_basic) > 0:
                final_pool = unused_basic
                match_type = "Alap"

    if not final_pool.empty:

        def calculate_freshness_score(row):
            score = 0
            cols = ['Target Muscle Group', 'Prime Mover Muscle', 'Secondary Muscle', 'Tertiary Muscle']
            
            for col in cols:
                if col in row.index:
                    izom = str(row[col]).strip()
                    if izom.lower() not in ['nan', 'none', ''] and izom not in worked_muscles:
                        score += 1
            return score

        candidates = final_pool.copy()
        candidates['freshness_score'] = candidates.apply(calculate_freshness_score, axis=1)
        
        max_score = candidates['freshness_score'].max()
        best_candidates = candidates[candidates['freshness_score'] == max_score]
        
        return best_candidates.sample(1).iloc[0], match_type

    return None, "Nincs találat"

def general_terv_quota(df, nehezseg, izom_fokusz, stilus):
    print(f"\n--- Tervezés: {izom_fokusz} ({nehezseg}) - Stílus: {stilus} ---")
    
    if izom_fokusz == 'Full Body': slots = ['Legs', 'Push', 'Pull', 'Core', 'Legs', 'Push']
    elif izom_fokusz == 'Lower Body': slots = ['Legs', 'Legs', 'Legs', 'Calves', 'Core', 'Legs']
    elif izom_fokusz == 'Upper Body': slots = ['Chest', 'Back', 'Shoulders', 'Arms', 'Chest', 'Back']
    elif izom_fokusz == 'Core': slots = ['Core', 'Core', 'Core', 'Lower Back', 'Core', 'Full Body']
    else: slots = ['Full Body', 'Legs', 'Push', 'Pull', 'Core', 'Full Body']

    edzesterv = []
    hasznalt_nevek = set()
    worked_muscles = set()

    for slot in slots:
        gyakorlat, info = find_best_exercise(df, slot, nehezseg, stilus, hasznalt_nevek, worked_muscles)
        
        if gyakorlat is not None:
            edzesterv.append(gyakorlat)
            hasznalt_nevek.add(gyakorlat['Exercise'])
            
            cols = ['Target Muscle Group', 'Prime Mover Muscle', 'Secondary Muscle', 'Tertiary Muscle']
            for col in cols:
                if col in gyakorlat.index:
                    izom = str(gyakorlat[col]).strip()
                    if izom.lower() not in ['nan', 'none', '']:
                        worked_muscles.add(izom)
        else:

            gyakorlat, info = find_best_exercise(df, 'Full Body', nehezseg, None, hasznalt_nevek, worked_muscles)
            if gyakorlat is not None:
                edzesterv.append(gyakorlat)
                hasznalt_nevek.add(gyakorlat['Exercise'])
                cols = ['Target Muscle Group', 'Prime Mover Muscle', 'Secondary Muscle', 'Tertiary Muscle']
                for col in cols:
                    if col in gyakorlat.index:
                        izom = str(gyakorlat[col]).strip()
                        if izom.lower() not in ['nan', 'none', '']:
                            worked_muscles.add(izom)

    if not edzesterv:
        return pd.DataFrame()

    edzesterv_df = pd.DataFrame(edzesterv)

    kivant_oszlopok = ['Exercise', 'Target Muscle Group', 'Primary Equipment', 'Difficulty Level', 'Short YouTube Demonstration']
    letezo_oszlopok = [col for col in kivant_oszlopok if col in df.columns]
    
    vegso_df = edzesterv_df[letezo_oszlopok].copy()

    if 'Short YouTube Demonstration' in vegso_df.columns:
        def javit_url(url):
            szoveg = str(url).strip()
            if szoveg.lower() in ['nan', 'none', '', 'no video']: return None
            if 'video demonstration' in szoveg.lower(): return None
            if '.' not in szoveg: return None
            if not szoveg.startswith('http'): return f'https://{szoveg}'
            return szoveg
            
        vegso_df['Short YouTube Demonstration'] = vegso_df['Short YouTube Demonstration'].apply(javit_url)
    
    return vegso_df