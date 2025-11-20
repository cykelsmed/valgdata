#!/usr/bin/env python3
"""
Udvidet generel analyse af valgdata (udover køn).
Analyserer valgdeltagelse, stemmeslugere, erhverv og partistyrke.
"""

import pandas as pd
from pathlib import Path
import sys
import glob
import re
import argparse

def find_latest_file(pattern):
    """Find seneste fil baseret på modification time"""
    files = glob.glob(pattern)
    if not files:
        return None
    files.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)
    return files[0]

def rens_stilling(titel):
    """Simpel rensning af jobtitler for bedre gruppering"""
    if not isinstance(titel, str) or pd.isna(titel):
        return "Uoplyst"

    titel = titel.lower().strip()

    # Slå enslydende titler sammen
    if "studerende" in titel or "elev" in titel:
        return "Studerende"
    if "pensionist" in titel or "efterløn" in titel:
        return "Pensionist"
    if "lærer" in titel:
        return "Lærer"
    if "sygeplejerske" in titel or "sosu" in titel:
        return "Sygeplejerske/SOSU"
    if "konsulent" in titel:
        return "Konsulent"
    if "direktør" in titel or "leder" in titel or "chef" in titel:
        return "Direktør/Leder"
    if "ingeniør" in titel:
        return "Ingeniør"
    if "håndværker" in titel or "tømrer" in titel or "murer" in titel or "elektriker" in titel:
        return "Håndværker"
    if "pædagog" in titel:
        return "Pædagog"
    if "læge" in titel or "doktor" in titel:
        return "Læge"
    if "medarbejder" in titel:
        return "Medarbejder"
    if "selvstændig" in titel:
        return "Selvstændig"

    return titel.capitalize()

def lav_generel_analyse(output_dir='excel_output'):
    """Lav generel analyse af valgdata"""
    print("🔍 Starter generel valganalyse...")

    # Find filer i 03_Samlet_Alle_Valg folder
    samlet_dir = Path(output_dir) / '03_Samlet_Alle_Valg'

    kand_fil = find_latest_file(str(samlet_dir / 'kandidater_ALLE_VALG_*.xlsx'))
    res_fil = find_latest_file(str(samlet_dir / 'valgresultater_ALLE_VALG_*.xlsx'))

    if not kand_fil:
        print(f"❌ Mangler kandidat-fil i {samlet_dir}")
        return False

    if not res_fil:
        print(f"❌ Mangler valgresultater-fil i {samlet_dir}")
        return False

    # Læs data
    print(f"📖 Læser kandidater fra: {Path(kand_fil).name}")
    df_kand = pd.read_excel(kand_fil)

    print(f"📖 Læser resultater fra: {Path(res_fil).name}")
    df_res = pd.read_excel(res_fil)

    # Opret output fil i 00_START_HER
    output_file = Path(output_dir) / '00_START_HER' / 'Analyse_generel.xlsx'
    output_file.parent.mkdir(parents=True, exist_ok=True)

    writer = pd.ExcelWriter(output_file, engine='openpyxl')

    # --- ANALYSE 1: STEMMESLUGERE (Top 100) ---
    print("  • Analyserer stemmeslugere...")
    if 'PersonligeStemmer' in df_res.columns and 'Stemmeseddelnavn' in df_res.columns:
        # Fjern rækker uden kandidat (listestemmer)
        df_kandidat_stemmer = df_res[df_res['Stemmeseddelnavn'].notna()].copy()

        # Aggreger personlige stemmer per kandidat (hvis de optræder i flere områder)
        kandidat_stemmer = df_kandidat_stemmer.groupby(['KandidatId', 'Stemmeseddelnavn', 'ListeNavn', 'Kommune', 'Valgart']).agg({
            'PersonligeStemmer': 'sum'
        }).reset_index()

        # Sorter og tag top 100
        top_stemmer = kandidat_stemmer.nlargest(100, 'PersonligeStemmer')[
            ['Stemmeseddelnavn', 'ListeNavn', 'Kommune', 'Valgart', 'PersonligeStemmer']
        ]
        top_stemmer.columns = ['Navn', 'Parti', 'Kommune', 'Valgtype', 'Personlige Stemmer']
        top_stemmer.to_excel(writer, sheet_name='Top 100 Stemmeslugere', index=False)

        print(f"    → Top stemmemodtager: {top_stemmer.iloc[0]['Navn']} med {top_stemmer.iloc[0]['Personlige Stemmer']:,} stemmer")

    # --- ANALYSE 2: VALGDELTAGELSE PR. KOMMUNE ---
    print("  • Analyserer valgdeltagelse...")
    if 'ValgdeltagelseProcent' in df_res.columns and 'Kommune' in df_res.columns:
        # Beregn gennemsnit pr. kommune (vægtet efter antal stemmeberettigede)
        deltagelse_data = df_res[df_res['ValgdeltagelseProcent'].notna()].copy()

        # Gruppér pr. kommune og valgart
        deltagelse = deltagelse_data.groupby(['Kommune', 'Valgart']).agg({
            'ValgdeltagelseProcent': 'mean',
            'Stemmeberettigede': 'sum',
            'AfgivneStemmer': 'sum'
        }).reset_index()

        # Beregn vægtet gennemsnit
        deltagelse['ValgdeltagelseProcent'] = (deltagelse['AfgivneStemmer'] / deltagelse['Stemmeberettigede'] * 100).round(2)
        deltagelse = deltagelse.sort_values('ValgdeltagelseProcent', ascending=False)

        deltagelse_output = deltagelse[['Kommune', 'Valgart', 'ValgdeltagelseProcent', 'Stemmeberettigede', 'AfgivneStemmer']]
        deltagelse_output.columns = ['Kommune', 'Valgtype', 'Valgdeltagelse %', 'Stemmeberettigede', 'Afgivne Stemmer']
        deltagelse_output.to_excel(writer, sheet_name='Valgdeltagelse', index=False)

        print(f"    → Højeste deltagelse: {deltagelse.iloc[0]['Kommune']} ({deltagelse.iloc[0]['ValgdeltagelseProcent']:.1f}%)")
        print(f"    → Laveste deltagelse: {deltagelse.iloc[-1]['Kommune']} ({deltagelse.iloc[-1]['ValgdeltagelseProcent']:.1f}%)")

    # --- ANALYSE 3: ERHVERVSFORDELING ---
    print("  • Analyserer kandidaternes job...")
    if 'Stilling' in df_kand.columns:
        df_kand['JobKategori'] = df_kand['Stilling'].apply(rens_stilling)

        # Total jobfordeling
        job_stats = df_kand['JobKategori'].value_counts().reset_index()
        job_stats.columns = ['Jobtitel', 'Antal Kandidater']
        job_stats['Andel %'] = (job_stats['Antal Kandidater'] / len(df_kand) * 100).round(1)
        job_stats.head(100).to_excel(writer, sheet_name='Top Job-titler', index=False)

        # Job per parti (top 10 partier)
        top_partier = df_kand['ListeNavn'].value_counts().head(10).index
        df_top_partier = df_kand[df_kand['ListeNavn'].isin(top_partier)].copy()

        job_parti = pd.crosstab(df_top_partier['JobKategori'], df_top_partier['ListeNavn'], margins=True)
        job_parti = job_parti.sort_values('All', ascending=False).head(30)
        job_parti.to_excel(writer, sheet_name='Job per Parti')

        print(f"    → Mest almindelige job: {job_stats.iloc[0]['Jobtitel']} ({job_stats.iloc[0]['Antal Kandidater']} kandidater)")

    # --- ANALYSE 4: PARTISTYRKE (Antal kandidater vs. Stemmer) ---
    print("  • Analyserer partistyrke...")

    # Antal kandidater pr parti
    parti_kand = df_kand['ListeNavn'].value_counts().reset_index()
    parti_kand.columns = ['Parti', 'Antal Kandidater']

    # Totale personlige stemmer og listestemmer pr parti
    if 'ListeStemmer' in df_res.columns and 'PersonligeStemmer' in df_res.columns:
        # Aggreger stemmer pr parti
        parti_stemmer = df_res.groupby('ListeNavn').agg({
            'ListeStemmer': 'sum',
            'PersonligeStemmer': lambda x: x.sum() if x.notna().any() else 0
        }).reset_index()
        parti_stemmer.columns = ['Parti', 'Listestemmer Total', 'Personlige Stemmer Total']
        parti_stemmer['Totale Stemmer'] = parti_stemmer['Listestemmer Total'] + parti_stemmer['Personlige Stemmer Total']

        # Merge med kandidatantal
        parti_stats = pd.merge(parti_kand, parti_stemmer, on='Parti', how='left')
        parti_stats['Stemmer per Kandidat'] = (parti_stats['Totale Stemmer'] / parti_stats['Antal Kandidater']).round(0)
        parti_stats = parti_stats.sort_values('Totale Stemmer', ascending=False)

        parti_stats.to_excel(writer, sheet_name='Partistatistik', index=False)

        print(f"    → Parti med flest stemmer: {parti_stats.iloc[0]['Parti']} ({parti_stats.iloc[0]['Totale Stemmer']:,.0f} stemmer)")
    else:
        parti_kand = parti_kand.sort_values('Antal Kandidater', ascending=False)
        parti_kand.to_excel(writer, sheet_name='Partistatistik', index=False)

    # --- ANALYSE 5: GEOGRAFI (Bor kandidaten i kommunen?) ---
    print("  • Analyserer kandidaternes bopæl...")
    if 'Bopæl' in df_kand.columns and 'KommuneNavn' in df_kand.columns:
        df_geo = df_kand[df_kand['Bopæl'].notna() & df_kand['KommuneNavn'].notna()].copy()

        # Simpel check: Er bopæl indeholdt i kommunenavnet?
        df_geo['LokalKandidat'] = df_geo.apply(
            lambda x: str(x['Bopæl']).lower() in str(x['KommuneNavn']).lower(),
            axis=1
        )

        # Total statistik
        lokal_stats = df_geo['LokalKandidat'].value_counts().reset_index()
        lokal_stats.columns = ['Bor i Kommunen (Estimat)', 'Antal']
        lokal_stats['Andel %'] = (lokal_stats['Antal'] / len(df_geo) * 100).round(1)
        lokal_stats.to_excel(writer, sheet_name='Geografi - Total', index=False)

        # Per parti
        geo_parti = df_geo.groupby(['ListeNavn', 'LokalKandidat']).size().unstack(fill_value=0)
        geo_parti['Total'] = geo_parti.sum(axis=1)
        geo_parti['% Lokale'] = (geo_parti[True] / geo_parti['Total'] * 100).round(1)
        geo_parti = geo_parti.sort_values('% Lokale', ascending=False)
        geo_parti.to_excel(writer, sheet_name='Geografi - Per Parti')

        pct_lokal = (df_geo['LokalKandidat'].sum() / len(df_geo) * 100)
        print(f"    → Andel lokale kandidater: {pct_lokal:.1f}% (estimat)")

    # --- ANALYSE 6: KANDIDATER PER KOMMUNE ---
    print("  • Analyserer kandidater per kommune...")
    if 'KommuneNavn' in df_kand.columns:
        kommune_stats = df_kand[df_kand['KommuneNavn'].notna()].copy()

        # Antal kandidater per kommune
        kandidater_kommune = kommune_stats.groupby('KommuneNavn').agg({
            'KandidatId': 'count',
            'EstimeretKøn': lambda x: (x == 'K').sum(),
            'ListeNavn': 'nunique'
        }).reset_index()

        kandidater_kommune.columns = ['Kommune', 'Antal Kandidater', 'Antal Kvinder', 'Antal Partier']
        kandidater_kommune['% Kvinder'] = (kandidater_kommune['Antal Kvinder'] / kandidater_kommune['Antal Kandidater'] * 100).round(1)
        kandidater_kommune = kandidater_kommune.sort_values('Antal Kandidater', ascending=False)

        kandidater_kommune.to_excel(writer, sheet_name='Kandidater per Kommune', index=False)

        print(f"    → Kommune med flest kandidater: {kandidater_kommune.iloc[0]['Kommune']} ({kandidater_kommune.iloc[0]['Antal Kandidater']} kandidater)")

    writer.close()
    print(f"✅ Generel analyse gemt: {output_file}")
    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Lav generel valganalyse')
    parser.add_argument('--output-dir', default='excel_output', help='Output directory')
    args = parser.parse_args()

    success = lav_generel_analyse(args.output_dir)
    sys.exit(0 if success else 1)
