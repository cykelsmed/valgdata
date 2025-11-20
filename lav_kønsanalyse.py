#!/usr/bin/env python3
"""
Laver kønsanalyse baseret på valgdata med estimeret køn
"""

import pandas as pd
from pathlib import Path
import sys
import glob

def find_latest_file(pattern):
    """Find den nyeste fil der matcher pattern"""
    files = glob.glob(pattern)
    if not files:
        return None
    # Sorter efter modificeringstid, nyeste først
    files.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)
    return files[0]

def lav_kønsanalyse(output_dir='excel_output'):
    """Lav omfattende kønsanalyse af valgdata"""

    # Find nyeste filer automatisk
    print("Finder nyeste datafiler...")
    kandidater_fil = find_latest_file(f'{output_dir}/kandidater_ALLE_VALG_*.xlsx')
    mandater_kommunal_fil = find_latest_file(f'{output_dir}/mandatfordeling_KOMMUNAL_*.xlsx')
    mandater_regional_fil = find_latest_file(f'{output_dir}/mandatfordeling_REGIONAL_*.xlsx')

    if not kandidater_fil:
        print(f"❌ Fejl: Kunne ikke finde kandidater_ALLE_VALG_*.xlsx i {output_dir}/")
        sys.exit(1)

    print(f"Bruger filer:")
    print(f"  • {Path(kandidater_fil).name}")
    if mandater_kommunal_fil:
        print(f"  • {Path(mandater_kommunal_fil).name}")
    if mandater_regional_fil:
        print(f"  • {Path(mandater_regional_fil).name}")

    # Læs kandidat- og mandatdata
    print("\nLæser data...")
    kandidater = pd.read_excel(kandidater_fil)
    mandater_kommunal = pd.read_excel(mandater_kommunal_fil) if mandater_kommunal_fil else None
    mandater_regional = pd.read_excel(mandater_regional_fil) if mandater_regional_fil else None

    # Fjern "Ukendt" køn fra detaljerede analyser (men behold i totaler)
    kandidater_kendt = kandidater[kandidater['EstimeretKøn'].isin(['M', 'K'])].copy()

    print(f"Total kandidater: {len(kandidater)}")
    print(f"Med kendt køn: {len(kandidater_kendt)}")

    # ARK 1: OVERSIGT
    oversigt_data = []

    # Total fordeling
    total_køn = kandidater['EstimeretKøn'].value_counts()
    oversigt_data.append({
        'Kategori': 'ALLE KANDIDATER',
        'Mænd (M)': total_køn.get('M', 0),
        'Kvinder (K)': total_køn.get('K', 0),
        'Ukendt': total_køn.get('Ukendt', 0),
        'Total': len(kandidater),
        'Andel Kvinder %': round(total_køn.get('K', 0) / (total_køn.get('M', 0) + total_køn.get('K', 0)) * 100, 1) if (total_køn.get('M', 0) + total_køn.get('K', 0)) > 0 else 0
    })

    # Kommunalvalg
    kommunal = kandidater[kandidater['ValgNavn'].str.contains('Kommunalvalg', na=False)]
    k_køn = kommunal['EstimeretKøn'].value_counts()
    oversigt_data.append({
        'Kategori': 'Kommunalvalg',
        'Mænd (M)': k_køn.get('M', 0),
        'Kvinder (K)': k_køn.get('K', 0),
        'Ukendt': k_køn.get('Ukendt', 0),
        'Total': len(kommunal),
        'Andel Kvinder %': round(k_køn.get('K', 0) / (k_køn.get('M', 0) + k_køn.get('K', 0)) * 100, 1) if (k_køn.get('M', 0) + k_køn.get('K', 0)) > 0 else 0
    })

    # Regionsrådsvalg
    regional = kandidater[kandidater['ValgNavn'].str.contains('Regionsrådsvalg', na=False)]
    r_køn = regional['EstimeretKøn'].value_counts()
    oversigt_data.append({
        'Kategori': 'Regionsrådsvalg',
        'Mænd (M)': r_køn.get('M', 0),
        'Kvinder (K)': r_køn.get('K', 0),
        'Ukendt': r_køn.get('Ukendt', 0),
        'Total': len(regional),
        'Andel Kvinder %': round(r_køn.get('K', 0) / (r_køn.get('M', 0) + r_køn.get('K', 0)) * 100, 1) if (r_køn.get('M', 0) + r_køn.get('K', 0)) > 0 else 0
    })

    df_oversigt = pd.DataFrame(oversigt_data)

    # ARK 2: KØNSFORDELING PER PARTI
    parti_køn = kandidater_kendt.groupby(['ListeNavn', 'EstimeretKøn']).size().unstack(fill_value=0)
    parti_køn['Total'] = parti_køn.sum(axis=1)
    parti_køn['Andel Kvinder %'] = round(parti_køn['K'] / (parti_køn['M'] + parti_køn['K']) * 100, 1)
    parti_køn = parti_køn.sort_values('Andel Kvinder %', ascending=False)
    parti_køn = parti_køn.reset_index()
    parti_køn.columns.name = None

    # ARK 3: KØNSFORDELING PER KOMMUNE (top 30)
    kommune_køn = kandidater_kendt[kandidater_kendt['KommuneNavn'] != ''].groupby(['KommuneNavn', 'EstimeretKøn']).size().unstack(fill_value=0)
    kommune_køn['Total'] = kommune_køn.sum(axis=1)
    kommune_køn['Andel Kvinder %'] = round(kommune_køn['K'] / (kommune_køn['M'] + kommune_køn['K']) * 100, 1)
    kommune_køn = kommune_køn.sort_values('Total', ascending=False).head(30)
    kommune_køn = kommune_køn.reset_index()
    kommune_køn.columns.name = None

    # ARK 4: KØNSFORDELING PER REGION
    region_køn = kandidater_kendt[kandidater_kendt['RegionNavn'] != ''].groupby(['RegionNavn', 'EstimeretKøn']).size().unstack(fill_value=0)
    region_køn['Total'] = region_køn.sum(axis=1)
    region_køn['Andel Kvinder %'] = round(region_køn['K'] / (region_køn['M'] + region_køn['K']) * 100, 1)
    region_køn = region_køn.sort_values('Andel Kvinder %', ascending=False)
    region_køn = region_køn.reset_index()
    region_køn.columns.name = None

    # ARK 5: ESTIMERINGSMETODER
    metode_stats = kandidater.groupby(['KønsMetode', 'EstimeretKøn']).size().unstack(fill_value=0)
    metode_stats['Total'] = metode_stats.sum(axis=1)
    metode_stats = metode_stats.reset_index()
    metode_stats.columns.name = None

    # ARK 6: TOP PARTIER MED BEDST KØNSBALANCE
    # Kun partier med mindst 50 kandidater
    store_partier = parti_køn[parti_køn['Total'] >= 50].copy()
    store_partier['Afvigelse fra 50%'] = abs(store_partier['Andel Kvinder %'] - 50)
    bedste_balance = store_partier.sort_values('Afvigelse fra 50%').head(20)

    # Gem til Excel
    output_fil = f'{output_dir}/Analyse_kønsfordeling.xlsx'
    print(f"\nGemmer kønsanalyse til {output_fil}...")

    with pd.ExcelWriter(output_fil, engine='openpyxl') as writer:
        df_oversigt.to_excel(writer, sheet_name='Oversigt', index=False)
        parti_køn.to_excel(writer, sheet_name='Per Parti', index=False)
        kommune_køn.to_excel(writer, sheet_name='Per Kommune (Top 30)', index=False)
        region_køn.to_excel(writer, sheet_name='Per Region', index=False)
        metode_stats.to_excel(writer, sheet_name='Estimeringsmetoder', index=False)
        bedste_balance.to_excel(writer, sheet_name='Bedste Kønsbalance', index=False)

    print("✅ Kønsanalyse færdig!")
    print(f"\n📊 HOVEDRESULTATER:")
    print(f"   • Total: {len(kandidater)} kandidater")
    print(f"   • Mænd: {total_køn.get('M', 0)} ({round(total_køn.get('M', 0)/len(kandidater)*100, 1)}%)")
    print(f"   • Kvinder: {total_køn.get('K', 0)} ({round(total_køn.get('K', 0)/len(kandidater)*100, 1)}%)")
    print(f"   • Ukendt: {total_køn.get('Ukendt', 0)} ({round(total_køn.get('Ukendt', 0)/len(kandidater)*100, 1)}%)")
    print(f"\n📁 Fil gemt: {output_fil}")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Lav kønsanalyse af valgdata')
    parser.add_argument('--output-dir', default='excel_output',
                       help='Output directory (default: excel_output)')

    args = parser.parse_args()
    lav_kønsanalyse(args.output_dir)
