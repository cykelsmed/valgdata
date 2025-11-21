#!/usr/bin/env python3
"""
Udvidet generel analyse af valgdata (udover køn).
Analyserer valgdeltagelse, stemmeslugere, erhverv og partistyrke.
"""

import pandas as pd
from pathlib import Path
import sys
import re
import argparse
from utils import find_latest_file, load_parquet

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

    # Find filer - Parquet først, derefter Excel fallback
    parquet_dir = Path(output_dir) / 'parquet'
    samlet_dir = Path(output_dir) / '03_Samlet_Alle_Valg'

    kand_fil = find_latest_file(str(parquet_dir / 'kandidater_ALLE_VALG_*.parquet'))
    if not kand_fil:
        kand_fil = find_latest_file(str(samlet_dir / 'kandidater_ALLE_VALG_*.xlsx'))
    if not kand_fil:
        kand_fil = find_latest_file(str(Path(output_dir) / 'kandidater_ALLE_VALG_*.xlsx'))

    res_fil = find_latest_file(str(parquet_dir / 'valgresultater_ALLE_VALG_*.parquet'))
    if not res_fil:
        res_fil = find_latest_file(str(samlet_dir / 'valgresultater_ALLE_VALG_*.xlsx'))
    if not res_fil:
        res_fil = find_latest_file(str(Path(output_dir) / 'valgresultater_ALLE_VALG_*.xlsx'))

    if not kand_fil:
        print(f"❌ Mangler kandidat-fil")
        return False

    if not res_fil:
        print(f"❌ Mangler valgresultater-fil")
        return False

    # Læs data - auto-detect format
    print(f"📖 Læser kandidater fra: {Path(kand_fil).name}")
    if kand_fil.endswith('.parquet'):
        df_kand = load_parquet(kand_fil)
    else:
        df_kand = pd.read_excel(kand_fil)

    print(f"📖 Læser resultater fra: {Path(res_fil).name}")
    if res_fil.endswith('.parquet'):
        df_res = load_parquet(res_fil)
    else:
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
        # VIGTIG FIX: Listestemmer er per afstemningsområde, ikke per kandidat!
        # Vi skal deduplikere listestemmer per parti+afstemningsområde

        # 1. Listestemmer - kun én gang per parti per afstemningsområde
        liste_stemmer = df_res[['ListeNavn', 'AfstemningsområdeDagiId', 'ListeStemmer']].drop_duplicates()
        parti_liste = liste_stemmer.groupby('ListeNavn')['ListeStemmer'].sum().reset_index()
        parti_liste.columns = ['Parti', 'Listestemmer Total']

        # 2. Personlige stemmer - summeres direkte (unikke per kandidat)
        parti_personlige = df_res.groupby('ListeNavn')['PersonligeStemmer'].sum().reset_index()
        parti_personlige.columns = ['Parti', 'Personlige Stemmer Total']

        # 3. Merge
        parti_stemmer = pd.merge(parti_liste, parti_personlige, on='Parti', how='outer')
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

    # --- ANALYSE 5: GEOGRAFI - FJERNET ---
    # Note: Geografisk analyse (lokale vs eksterne kandidater) er fjernet
    # fordi dataene er for upræcise. Bopæl indeholder kun by-navn (fx "Viby J"),
    # ikke kommune, hvilket giver mange false negatives.
    # En korrekt analyse ville kræve postnummer → kommune mapping.
    print("  • Geografisk analyse sprunget over (upræcise data)")

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

def main(output_dir='excel_output'):
    """Main funktion til brug i pipeline"""
    success = lav_generel_analyse(output_dir)
    return success

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Lav generel valganalyse')
    parser.add_argument('--output-dir', default='excel_output', help='Output directory')
    args = parser.parse_args()

    success = main(args.output_dir)
    sys.exit(0 if success else 1)
