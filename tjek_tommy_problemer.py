#!/usr/bin/env python3
"""
Script til at verificere Tommys observationer om uoverensstemmelser
"""

import pandas as pd
from pathlib import Path
from utils import find_latest_file, load_parquet

def tjek_hjørring_venstre():
    """Tjek specifikt Venstre i Hjørring som Tommy rapporterede"""

    print("="*80)
    print("TJEK AF TOMMYS OBSERVATIONER")
    print("="*80)

    # Find nyeste valgresultater fil
    parquet_dir = Path('excel_output/parquet')
    samlet_dir = Path('excel_output/03_Samlet_Alle_Valg')

    res_fil = find_latest_file(str(parquet_dir / 'valgresultater_KOMMUNAL_*.parquet'))
    if not res_fil:
        res_fil = find_latest_file(str(samlet_dir / 'valgresultater_KOMMUNAL_*.xlsx'))
    if not res_fil:
        res_fil = find_latest_file('excel_output/valgresultater_KOMMUNAL_*.xlsx')

    if not res_fil:
        print("❌ Kunne ikke finde valgresultater fil")
        return

    print(f"\n📖 Læser: {Path(res_fil).name}")

    if res_fil.endswith('.parquet'):
        df = load_parquet(res_fil)
    else:
        df = pd.read_excel(res_fil)

    # Filtrer på Hjørring Kommune, Venstre (ikke Radikale Venstre!)
    hjørring_v = df[
        (df['Kommune'] == 'Hjørring Kommune') &
        (df['ListeNavn'] == 'Venstre, Danmarks Liberale Parti')
    ].copy()

    print(f"\n📊 HJØRRING KOMMUNE - VENSTRE")
    print(f"   Antal rækker: {len(hjørring_v)}")

    # Tjek om der er duplikater
    if 'FrigivelsesTidspunkt' in df.columns and 'KandidatId' in df.columns:
        print(f"\n🔍 TJEK FOR DUPLIKATER")

        # Unikke tidsstempler
        tidsstempler = hjørring_v['FrigivelsesTidspunkt'].unique()
        print(f"   Unikke FrigivelsesTidspunkt: {len(tidsstempler)}")
        for ts in sorted(tidsstempler):
            count = len(hjørring_v[hjørring_v['FrigivelsesTidspunkt'] == ts])
            print(f"      {ts}: {count} rækker")

        # Tjek for duplicate kandidater
        if 'AfstemningsområdeDagiId' in df.columns:
            duplikater = hjørring_v.duplicated(
                subset=['AfstemningsområdeDagiId', 'KandidatId'],
                keep=False
            )
            if duplikater.any():
                print(f"\n   ⚠️  FUNDET {duplikater.sum()} DUPLIKAT-RÆKKER!")
                print(f"   Dette kan forklare uoverensstemmelserne!")

    # Beregn totaler per afstemningsområde
    print(f"\n📋 SPECIFIK TJEK AF TOMMYS EKSEMPLER:")

    # Bindslev (brug ListeStemmer = personlige + listestemmer)
    bindslev = hjørring_v[hjørring_v['Afstemningsområde'].str.contains('Bindslev', na=False)]
    if len(bindslev) > 0:
        bindslev_total = bindslev.groupby('AfstemningsområdeDagiId')['ListeStemmer'].first().sum()
        print(f"\n   Bindslev:")
        print(f"      Vores data: {bindslev_total} stemmer")
        print(f"      valg.dk:    401 stemmer")
        print(f"      Difference: {bindslev_total - 401}")
        if bindslev_total == 401:
            print(f"      ✅ PERFEKT MATCH!")

    # Hjørring Vest (brug ListeStemmer = personlige + listestemmer)
    vest = hjørring_v[hjørring_v['Afstemningsområde'].str.contains('Vest', na=False)]
    if len(vest) > 0:
        vest_total = vest.groupby('AfstemningsområdeDagiId')['ListeStemmer'].first().sum()
        print(f"\n   Hjørring Vest:")
        print(f"      Vores data: {vest_total} stemmer")
        print(f"      valg.dk:    631 stemmer")
        print(f"      Difference: {vest_total - 631}")
        if vest_total == 631:
            print(f"      ✅ PERFEKT MATCH!")

        # Søren Smalbro specifikt (personlige stemmer)
        smalbro = vest[vest['Stemmeseddelnavn'].str.contains('Smalbro', na=False)]
        if len(smalbro) > 0:
            smalbro_sum = smalbro['PersonligeStemmer'].sum()
            print(f"\n   Søren Smalbro (Hjørring Vest):")
            print(f"      Vores data: {smalbro_sum} stemmer")
            print(f"      valg.dk:    220 stemmer")
            print(f"      Difference: {smalbro_sum - 220}")
            if smalbro_sum == 220:
                print(f"      ✅ PERFEKT MATCH!")

    # Total for Venstre i Hjørring
    total_personlige = hjørring_v['PersonligeStemmer'].sum()
    print(f"\n📊 TOTAL VENSTRE I HJØRRING:")
    print(f"   Personlige stemmer (sum): {total_personlige}")
    print(f"   valg.dk total:            8037")
    print(f"   Difference:               {total_personlige - 8037}")

    # Tjek også listestemmer
    if 'Listestemmer' in hjørring_v.columns:
        # Dedupliker listestemmer
        liste_dedup = hjørring_v[['AfstemningsområdeDagiId', 'Listestemmer']].drop_duplicates()
        listestemmer_sum = liste_dedup['Listestemmer'].sum()
        total_med_liste = total_personlige + listestemmer_sum

        print(f"\n   Med listestemmer:")
        print(f"      Personlige: {total_personlige}")
        print(f"      Liste:      {listestemmer_sum}")
        print(f"      Total:      {total_med_liste}")
        if total_med_liste == 8037:
            print(f"      ✅ PERFEKT MATCH MED VALG.DK!")

if __name__ == '__main__':
    tjek_hjørring_venstre()
