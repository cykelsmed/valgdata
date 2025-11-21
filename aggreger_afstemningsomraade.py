#!/usr/bin/env python3
"""
Aggreger valgresultater per afstemningsområde + parti

Giver kommune, afstemningsområde, adresse, parti og totale stemmer.
Perfekt til geografiske kort.
"""

import pandas as pd
from pathlib import Path
from utils import find_latest_file, load_parquet

def aggreger_afstemningsomraade(valgtype='KOMMUNAL'):
    """Aggreger valgresultater per afstemningsområde + parti"""

    print(f"📍 Aggregerer {valgtype} per afstemningsområde...")

    # 1. Load afstemningsområder med geografisk data
    geo_dir = Path('excel_output/04_Reference_Geografi')
    afstem_fil = find_latest_file(str(geo_dir / 'Afstemningsomraade-*.xlsx'))

    if not afstem_fil:
        print("❌ Kunne ikke finde afstemningsområde-fil")
        return None

    print(f"📖 Læser geografisk data: {Path(afstem_fil).name}")
    afstem = pd.read_excel(afstem_fil)

    # Behold relevante kolonner
    geo_data = afstem[[
        'Dagi_id',
        'Navn',
        'Kommunekode',
        'Afstemningssted.Navn',
        'Afstemningssted.Adgangsadresse.Adressebetegnelse'
    ]].copy()

    geo_data.rename(columns={
        'Navn': 'Afstemningsområde',
        'Afstemningssted.Navn': 'Afstemningssted',
        'Afstemningssted.Adgangsadresse.Adressebetegnelse': 'Adresse'
    }, inplace=True)

    # 2. Load valgresultater
    parquet_dir = Path('excel_output/parquet')
    valgres_fil = find_latest_file(str(parquet_dir / f'valgresultater_{valgtype}_*.parquet'))

    if not valgres_fil:
        print(f"❌ Kunne ikke finde valgresultater for {valgtype}")
        return None

    print(f"📖 Læser valgresultater: {Path(valgres_fil).name}")
    valgres = load_parquet(valgres_fil)

    # 3. Dedupliker ListeStemmer per område + parti (kun én gang per område)
    print(f"📊 Deduplikerer og aggregerer...")
    valgres_dedup = valgres.groupby(
        ['Kommune', 'AfstemningsområdeDagiId', 'Afstemningsområde', 'ListeNavn']
    )['ListeStemmer'].first().reset_index()

    # 4. Join med geografisk data
    print(f"🔗 Joiner med geografisk data...")
    resultat = valgres_dedup.merge(
        geo_data,
        left_on='AfstemningsområdeDagiId',
        right_on='Dagi_id',
        how='left'
    )

    # Drop duplikerede kolonner
    resultat = resultat[[
        'Kommune',
        'Afstemningsområde_x',
        'Afstemningssted',
        'Adresse',
        'ListeNavn',
        'ListeStemmer',
        'AfstemningsområdeDagiId'
    ]].copy()

    resultat.rename(columns={
        'Afstemningsområde_x': 'Afstemningsområde',
        'ListeStemmer': 'TotalStemmer'
    }, inplace=True)

    # Sorter
    resultat = resultat.sort_values(
        ['Kommune', 'Afstemningsområde', 'TotalStemmer'],
        ascending=[True, True, False]
    )

    print(f"✅ {len(resultat):,} rækker genereret")
    print(f"   {resultat['Kommune'].nunique()} kommuner")
    print(f"   {resultat['Afstemningsområde'].nunique()} afstemningsområder")
    print(f"   {resultat['ListeNavn'].nunique()} partier")

    return resultat

def main():
    print("="*80)
    print("AGGREGERING PER AFSTEMNINGSOMRÅDE")
    print("="*80)
    print()

    # Lav begge valgtyper
    for valgtype in ['KOMMUNAL', 'REGIONAL']:
        print()
        resultat = aggreger_afstemningsomraade(valgtype)

        if resultat is not None:
            # Gem til Excel
            output_dir = Path('excel_output/03_Samlet_Alle_Valg')
            output_dir.mkdir(parents=True, exist_ok=True)

            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')

            valgart_navn = 'Kommunal' if valgtype == 'KOMMUNAL' else 'Regionsraads'
            output_fil = output_dir / f'resultater_per_afstemningsomraade_{valgart_navn}_{timestamp}.xlsx'

            resultat.to_excel(output_fil, index=False, engine='openpyxl')
            print(f"💾 Gemt: {output_fil.name}")

            # Vis preview
            print(f"\n👀 Preview ({valgart_navn}):")
            print(resultat.head(20).to_string(index=False))

if __name__ == '__main__':
    main()
