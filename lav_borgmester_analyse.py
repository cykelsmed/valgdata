#!/usr/bin/env python3
"""
Laver borgmester-analyse baseret på parsed borgmester-data
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
    files.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)
    return files[0]

def lav_borgmester_analyse(output_dir='excel_output'):
    """Lav omfattende borgmester-analyse"""

    # Læs borgmester CSV
    print("Læser borgmester-data...")
    if not Path('borgmestre_parsed.csv').exists():
        print("❌ Fejl: borgmestre_parsed.csv findes ikke!")
        print("Kør først: python3 parse_borgmestre.py")
        sys.exit(1)

    borgmestre = pd.read_csv('borgmestre_parsed.csv')
    print(f"Læste {len(borgmestre)} borgmestre")

    # Find kandidat-fil med kønsdata
    samlet_dir = Path(output_dir) / '03_Samlet_Alle_Valg'
    kandidater_fil = find_latest_file(f'{samlet_dir}/kandidater_ALLE_VALG_*.xlsx')
    if not kandidater_fil:
        kandidater_fil = find_latest_file(f'{output_dir}/kandidater_ALLE_VALG_*.xlsx')

    # Match med kønsdata hvis muligt
    if kandidater_fil:
        print(f"\nMatcher med kønsdata fra {Path(kandidater_fil).name}...")
        kandidater = pd.read_excel(kandidater_fil)

        # Opret kønsmap baseret på fornavn
        koen_map = {}
        for _, row in kandidater.iterrows():
            fornavn = str(row.get('Fornavn', '')).strip()
            koen = row.get('EstimeretKøn', 'Ukendt')
            if fornavn and koen in ['M', 'K']:
                koen_map[fornavn] = koen

        # Match borgmestre med køn baseret på fornavn
        def get_koen(navn):
            fornavn = str(navn).split()[0] if navn else ''
            return koen_map.get(fornavn, 'Ukendt')

        borgmestre['Køn'] = borgmestre['Navn'].apply(get_koen)
        print(f"Matchede køn for {len(borgmestre[borgmestre['Køn'] != 'Ukendt'])} borgmestre")
    else:
        print("\n⚠️  Kunne ikke finde kandidat-fil - kønsanalyse springer over")
        borgmestre['Køn'] = 'Ukendt'

    # ARK 1: OVERSIGT
    oversigt = borgmestre[['Kommune', 'Navn', 'Status', 'Parti', 'PersonligeStemmer', 'Køn']].copy()
    oversigt = oversigt.sort_values('PersonligeStemmer', ascending=False)

    # ARK 2: PARTIFORDELING
    parti_fordeling = borgmestre.groupby('Parti').size().reset_index(name='Antal Borgmestre')
    parti_fordeling = parti_fordeling.sort_values('Antal Borgmestre', ascending=False)

    # Tilføj andel
    parti_fordeling['Andel %'] = round(parti_fordeling['Antal Borgmestre'] / len(borgmestre) * 100, 1)

    # ARK 3: STATUS FORDELING (Genvalgt/Magtskifte/Nyvalgt)
    status_fordeling = borgmestre.groupby('Status').size().reset_index(name='Antal')
    status_fordeling['Andel %'] = round(status_fordeling['Antal'] / len(borgmestre) * 100, 1)
    status_fordeling = status_fordeling.sort_values('Antal', ascending=False)

    # ARK 4: TOP 20 PERSONLIGE STEMMER
    top_stemmer = borgmestre[['Kommune', 'Navn', 'Parti', 'PersonligeStemmer', 'Status', 'Køn']].copy()
    top_stemmer = top_stemmer.sort_values('PersonligeStemmer', ascending=False).head(20)

    # ARK 5: KØNSFORDELING
    if 'Køn' in borgmestre.columns:
        koen_stats = []

        # Total kønsfordeling
        total_koen = borgmestre['Køn'].value_counts()
        koen_stats.append({
            'Kategori': 'ALLE BORGMESTRE',
            'Mænd (M)': total_koen.get('M', 0),
            'Kvinder (K)': total_koen.get('K', 0),
            'Ukendt': total_koen.get('Ukendt', 0),
            'Total': len(borgmestre),
            'Andel Kvinder %': round(total_koen.get('K', 0) / (total_koen.get('M', 0) + total_koen.get('K', 0)) * 100, 1) if (total_koen.get('M', 0) + total_koen.get('K', 0)) > 0 else 0
        })

        # Kønsfordeling per status
        for status in ['Genvalgt', 'Magtskifte', 'Nyvalgt']:
            subset = borgmestre[borgmestre['Status'] == status]
            koen = subset['Køn'].value_counts()
            koen_stats.append({
                'Kategori': status,
                'Mænd (M)': koen.get('M', 0),
                'Kvinder (K)': koen.get('K', 0),
                'Ukendt': koen.get('Ukendt', 0),
                'Total': len(subset),
                'Andel Kvinder %': round(koen.get('K', 0) / (koen.get('M', 0) + koen.get('K', 0)) * 100, 1) if (koen.get('M', 0) + koen.get('K', 0)) > 0 else 0
            })

        df_koen = pd.DataFrame(koen_stats)
    else:
        df_koen = pd.DataFrame({'Note': ['Kønsdata ikke tilgængelig']})

    # ARK 6: MAGTSKIFTER PER PARTI
    magtskifter = borgmestre[borgmestre['Status'] == 'Magtskifte'].groupby('Parti').size().reset_index(name='Antal Magtskifter')
    magtskifter = magtskifter.sort_values('Antal Magtskifter', ascending=False)

    # Gem til Excel
    output_file = Path(output_dir) / '00_START_HER' / 'Analyse_borgmestre.xlsx'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nGemmer borgmester-analyse til {output_file}...")

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        oversigt.to_excel(writer, sheet_name='Oversigt', index=False)
        parti_fordeling.to_excel(writer, sheet_name='Partifordeling', index=False)
        status_fordeling.to_excel(writer, sheet_name='Status (Genvalgt mv)', index=False)
        top_stemmer.to_excel(writer, sheet_name='Top 20 Stemmer', index=False)
        df_koen.to_excel(writer, sheet_name='Kønsfordeling', index=False)
        magtskifter.to_excel(writer, sheet_name='Magtskifter per Parti', index=False)

    print("✅ Borgmester-analyse færdig!")
    print(f"\n📊 HOVEDRESULTATER:")
    print(f"   • Total: {len(borgmestre)} borgmestre")
    print(f"   • Genvalgt: {len(borgmestre[borgmestre['Status'] == 'Genvalgt'])} ({round(len(borgmestre[borgmestre['Status'] == 'Genvalgt'])/len(borgmestre)*100, 1)}%)")
    print(f"   • Magtskifte: {len(borgmestre[borgmestre['Status'] == 'Magtskifte'])} ({round(len(borgmestre[borgmestre['Status'] == 'Magtskifte'])/len(borgmestre)*100, 1)}%)")
    print(f"   • Nyvalgt: {len(borgmestre[borgmestre['Status'] == 'Nyvalgt'])} ({round(len(borgmestre[borgmestre['Status'] == 'Nyvalgt'])/len(borgmestre)*100, 1)}%)")
    print(f"\n   • Største parti: {parti_fordeling.iloc[0]['Parti']} ({parti_fordeling.iloc[0]['Antal Borgmestre']} borgmestre)")

    if 'Køn' in borgmestre.columns and total_koen.get('M', 0) + total_koen.get('K', 0) > 0:
        andel_kvinder = round(total_koen.get('K', 0) / (total_koen.get('M', 0) + total_koen.get('K', 0)) * 100, 1)
        print(f"   • Kønsfordeling: {total_koen.get('M', 0)} mænd, {total_koen.get('K', 0)} kvinder ({andel_kvinder}% kvinder)")

    print(f"\n📁 Fil gemt: {output_file}")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Lav borgmester-analyse')
    parser.add_argument('--output-dir', default='excel_output',
                       help='Output directory (default: excel_output)')

    args = parser.parse_args()
    lav_borgmester_analyse(args.output_dir)
