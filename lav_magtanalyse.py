#!/usr/bin/env python3
"""
Magtanalyse - Fire politiske analyser:
1. De Tragiske Helte (Mandattyveri)
2. Enmandshæren (Dependency Ratio)
3. Geografiske Højborge (Afstemningsområde-analyse)
4. Tynde Flertaller (Konstitueringsrisiko)
"""

import pandas as pd
from pathlib import Path
import sys
import argparse
from utils import find_latest_file, load_parquet

def normalize_party_name(party_name):
    """
    Normaliser partinavne for at matche mellem forskellige datakilder.
    Borgmester-data bruger korte navne, mandatfordeling bruger fulde navne.
    """
    if pd.isna(party_name):
        return party_name

    # Mapping table for common party name variations
    normalization_map = {
        'SF - Socialistisk Folkeparti': 'Socialistisk Folkeparti',
        'Venstre, Danmarks Liberale Parti': 'Venstre',
        'Det Konservative Folkeparti': 'Konservative',
        'Enhedslisten - De Rød-Grønne': 'Enhedslisten',
        'Danmarksdemokraterne - Inger Støjberg': 'Danmarksdemokraterne',
    }

    return normalization_map.get(party_name, party_name)

def find_mandate_theft(df_res, df_mand):
    """
    Analyse 1: De Tragiske Helte - Kandidater der fik flere stemmer
    end den sidste valgte fra deres parti, men ikke blev valgt.
    """
    print("  • Analyserer mandattyveri (De Tragiske Helte)...")

    # Aggregate kandidat stemmer per kommune+parti
    kandidat_stemmer = df_res[df_res['Stemmeseddelnavn'].notna()].groupby([
        'Kommune', 'ListeNavn', 'KandidatId', 'Stemmeseddelnavn', 'Valgart'
    ]).agg({
        'PersonligeStemmer': 'sum'
    }).reset_index()

    # Get elected candidates per kommune+parti
    elected = df_mand[
        (df_mand['MandatType'].isin(['Personligt', 'Liste'])) &
        (df_mand['KandidatId'].notna())
    ].copy()

    robbed_candidates = []

    # Process each kommune+parti combination
    for (kommune, parti, valgart), group in kandidat_stemmer.groupby(['Kommune', 'ListeNavn', 'Valgart']):
        # Get elected from this parti+kommune
        elected_here = elected[
            (elected['Kommune'] == kommune) &
            (elected['ListeNavn'] == parti) &
            (elected['Valgart'] == valgart)
        ]

        if len(elected_here) == 0:
            continue  # No mandates won

        # Find last elected (highest mandate number)
        last_elected = elected_here.sort_values('MandatNummer').iloc[-1]
        last_elected_id = last_elected['KandidatId']

        # Get personal votes for last elected
        last_elected_votes = group[group['KandidatId'] == last_elected_id]
        if len(last_elected_votes) == 0:
            continue

        threshold = last_elected_votes.iloc[0]['PersonligeStemmer']

        # Find candidates with more votes but not elected
        elected_ids = set(elected_here['KandidatId'].tolist())

        for _, kandidat in group.iterrows():
            if (kandidat['PersonligeStemmer'] > threshold and
                kandidat['KandidatId'] not in elected_ids):
                robbed_candidates.append({
                    'Navn': kandidat['Stemmeseddelnavn'],
                    'Parti': parti,
                    'Kommune': kommune,
                    'Valgtype': valgart,
                    'Personlige Stemmer': kandidat['PersonligeStemmer'],
                    'Sidste Valgtes Stemmer': threshold,
                    'Stemmeoverskud': kandidat['PersonligeStemmer'] - threshold,
                    'Sidste Valgte': last_elected['Stemmeseddelnavn']
                })

    df_robbed = pd.DataFrame(robbed_candidates)

    if len(df_robbed) > 0:
        df_robbed = df_robbed.sort_values('Stemmeoverskud', ascending=False).head(100)
        print(f"    → Fandt {len(df_robbed)} tilfælde af 'mandattyveri'")
        if len(df_robbed) > 0:
            top = df_robbed.iloc[0]
            print(f"    → Værste tilfælde: {top['Navn']} ({top['Parti']}, {top['Kommune']}) - {top['Stemmeoverskud']:,} stemmer over grænsen")
    else:
        print("    → Ingen tilfælde fundet")

    return df_robbed


def find_one_person_armies(df_res):
    """
    Analyse 2: Enmandshæren - Kandidater der bærer hele partiet
    (høj dependency ratio)
    """
    print("  • Analyserer enmandshære (Dependency Ratio)...")

    kandidat_data = df_res[df_res['Stemmeseddelnavn'].notna()].copy()

    # Calculate party totals per kommune (avoid listestemmer duplication!)
    liste_stemmer_dedup = kandidat_data[['Kommune', 'ListeNavn', 'Valgart', 'AfstemningsområdeDagiId', 'ListeStemmer']].drop_duplicates()
    parti_liste = liste_stemmer_dedup.groupby(['Kommune', 'ListeNavn', 'Valgart'])['ListeStemmer'].sum().reset_index()
    parti_liste.columns = ['Kommune', 'ListeNavn', 'Valgart', 'PartiListeStemmer']

    # Personal votes per parti
    parti_personlige = kandidat_data.groupby(['Kommune', 'ListeNavn', 'Valgart']).agg({
        'PersonligeStemmer': 'sum'
    }).reset_index()
    parti_personlige.columns = ['Kommune', 'ListeNavn', 'Valgart', 'PartiPersonligeStemmer']

    # Merge
    parti_totals = pd.merge(parti_liste, parti_personlige, on=['Kommune', 'ListeNavn', 'Valgart'], how='outer')
    parti_totals['PartiTotalStemmer'] = parti_totals['PartiListeStemmer'].fillna(0) + parti_totals['PartiPersonligeStemmer'].fillna(0)

    # Calculate kandidat totals
    kandidat_totals = kandidat_data.groupby([
        'Kommune', 'ListeNavn', 'Valgart', 'KandidatId', 'Stemmeseddelnavn'
    ]).agg({
        'PersonligeStemmer': 'sum'
    }).reset_index()

    # Merge to get dependency ratio
    merged = pd.merge(
        kandidat_totals,
        parti_totals[['Kommune', 'ListeNavn', 'Valgart', 'PartiTotalStemmer']],
        on=['Kommune', 'ListeNavn', 'Valgart'],
        how='left'
    )

    # Calculate dependency ratio
    merged['Dependency Ratio %'] = (merged['PersonligeStemmer'] / merged['PartiTotalStemmer'] * 100).round(1)

    # Filter out 100% cases with very few votes (noise)
    merged = merged[
        ~((merged['Dependency Ratio %'] >= 99.9) & (merged['PartiTotalStemmer'] < 50))
    ]

    # Top 100
    top_dependency = merged.nlargest(100, 'Dependency Ratio %')[[
        'Stemmeseddelnavn', 'ListeNavn', 'Kommune', 'Valgart', 'PersonligeStemmer',
        'PartiTotalStemmer', 'Dependency Ratio %'
    ]].copy()

    top_dependency.columns = ['Navn', 'Parti', 'Kommune', 'Valgtype', 'Personlige Stemmer',
                              'Parti Total Stemmer', 'Dependency Ratio %']

    print(f"    → Top enmandshær: {top_dependency.iloc[0]['Navn']} ({top_dependency.iloc[0]['Parti']}, {top_dependency.iloc[0]['Kommune']}) - {top_dependency.iloc[0]['Dependency Ratio %']:.1f}% af partiets stemmer")

    return top_dependency


def find_geographic_strongholds(df_res):
    """
    Analyse 3: Geografiske Højborge - Afstemningsområder hvor
    partiet klarer sig meget bedre end kommunegennemsnittet
    """
    print("  • Analyserer geografiske højborge...")

    # Calculate party vote share per afstemningsområde
    # For each afstemningsområde: ListeStemmer + PersonligeStemmer for parti / Total Gyldige Stemmer

    # Deduplicate listestemmer
    area_data = df_res.copy()

    # Get total gyldige stemmer per område (use first row per område)
    area_totals = area_data.groupby(['AfstemningsområdeDagiId', 'Afstemningsområde', 'Kommune', 'Valgart']).agg({
        'GyldigeStemmer': 'first'  # Same for all rows in area
    }).reset_index()

    # Calculate parti votes per område
    # VIGTIGT: ListeStemmer (capital S) er ALLEREDE den totale sum for partiet
    # ListeStemmer = Listestemmer (blanke) + PersonligeStemmer (kandidater)
    # Så vi skal IKKE lægge sammen - bare bruge ListeStemmer direkte!

    # Deduplicate: ListeStemmer er samme værdi for alle kandidater i samme parti+område
    parti_area = area_data[['AfstemningsområdeDagiId', 'Afstemningsområde', 'Kommune', 'Valgart', 'ListeNavn', 'ListeStemmer']].drop_duplicates()

    # Rename for klarhed
    parti_area = parti_area.rename(columns={'ListeStemmer': 'PartiStemmer'})

    # Merge with totals
    parti_area = pd.merge(parti_area, area_totals,
                          on=['AfstemningsområdeDagiId', 'Afstemningsområde', 'Kommune', 'Valgart'],
                          how='left')

    # VALIDATION: PartiStemmer må ALDRIG være større end GyldigeStemmer
    invalid_rows = parti_area[parti_area['PartiStemmer'] > parti_area['GyldigeStemmer']]
    if len(invalid_rows) > 0:
        print(f"\n⚠️  ADVARSEL: Fandt {len(invalid_rows)} rækker hvor PartiStemmer > GyldigeStemmer")
        print("Dette indikerer en fejl i databehandlingen!")
        print(invalid_rows[['Kommune', 'Afstemningsområde', 'ListeNavn', 'PartiStemmer', 'GyldigeStemmer']].head(10))
        # Cap at 100% to prevent crashes
        parti_area.loc[parti_area['PartiStemmer'] > parti_area['GyldigeStemmer'], 'PartiStemmer'] = parti_area['GyldigeStemmer']

    # Calculate vote share per area
    parti_area['OmrådeAndel %'] = (parti_area['PartiStemmer'] / parti_area['GyldigeStemmer'] * 100).round(1)

    # Calculate kommune-gennemsnit for each parti
    kommune_avg = parti_area.groupby(['Kommune', 'Valgart', 'ListeNavn']).agg({
        'PartiStemmer': 'sum',
        'GyldigeStemmer': 'sum'
    }).reset_index()
    kommune_avg['KommuneGennemsnit %'] = (kommune_avg['PartiStemmer'] / kommune_avg['GyldigeStemmer'] * 100).round(1)

    # Merge
    parti_area = pd.merge(
        parti_area,
        kommune_avg[['Kommune', 'Valgart', 'ListeNavn', 'KommuneGennemsnit %']],
        on=['Kommune', 'Valgart', 'ListeNavn'],
        how='left'
    )

    # Calculate deviation
    parti_area['Afvigelse'] = parti_area['OmrådeAndel %'] - parti_area['KommuneGennemsnit %']

    # Filter: only areas with >10% positive deviation AND kommune avg > 2% (filter noise)
    strongholds = parti_area[
        (parti_area['Afvigelse'] > 10) &
        (parti_area['KommuneGennemsnit %'] > 2)
    ].copy()

    # Top 200 by deviation
    strongholds = strongholds.nlargest(200, 'Afvigelse')[[
        'ListeNavn', 'Kommune', 'Afstemningsområde', 'Valgart',
        'OmrådeAndel %', 'KommuneGennemsnit %', 'Afvigelse'
    ]].copy()

    strongholds.columns = ['Parti', 'Kommune', 'Afstemningsområde', 'Valgtype',
                           'Område %', 'Kommune Gennemsnit %', 'Afvigelse']

    if len(strongholds) > 0:
        top = strongholds.iloc[0]
        print(f"    → Stærkeste højborg: {top['Parti']} i {top['Afstemningsområde']}, {top['Kommune']} - {top['Afvigelse']:.1f}% over gennemsnit")
    else:
        print("    → Ingen højborge fundet")

    return strongholds


def find_thin_majorities(df_mand, output_dir):
    """
    Analyse 4: Tynde Flertaller - Kommuner hvor borgmesterens
    parti har mindst muligt flertal (risiko for kaos)
    """
    print("  • Analyserer tynde flertaller...")

    # Load borgmester data (check multiple locations)
    borgmester_fil = Path('borgmestre_parsed.csv')
    if not borgmester_fil.exists():
        borgmester_fil = Path(output_dir) / 'borgmestre_parsed.csv'
    if not borgmester_fil.exists():
        print("    ⚠️ Mangler borgmestre_parsed.csv - springer analyse over")
        return pd.DataFrame()

    df_borg = pd.read_csv(borgmester_fil)

    # Count mandates per kommune+parti (only Kommunalvalg, exclude Stedfortræder)
    mandater = df_mand[
        (df_mand['Valgart'] == 'Kommunalvalg') &
        (df_mand['MandatType'] != 'Stedfortræder')
    ].copy()

    # Normalize party names to match borgmester data
    mandater['PartiNormaliseret'] = mandater['ListeNavn'].apply(normalize_party_name)

    # Count mandates per parti
    parti_mandater = mandater.groupby(['Kommune', 'PartiNormaliseret']).size().reset_index(name='Mandater')

    # Total mandates per kommune
    total_mandater = mandater.groupby('Kommune').size().reset_index(name='Total Mandater')

    thin_majorities = []

    for _, borg in df_borg.iterrows():
        kommune = borg['Kommune']
        borgmester_parti = borg['Parti']
        borgmester_navn = borg['Navn']

        # Get mandates for this kommune
        kommune_mandater = parti_mandater[parti_mandater['Kommune'] == kommune]
        kommune_total = total_mandater[total_mandater['Kommune'] == kommune]

        if len(kommune_total) == 0:
            continue

        total = kommune_total.iloc[0]['Total Mandater']
        simple_majority = total / 2

        # Get borgmester parti mandates (using normalized name)
        borg_parti_row = kommune_mandater[kommune_mandater['PartiNormaliseret'] == borgmester_parti]

        if len(borg_parti_row) == 0:
            # Borgmester parti has 0 mandates (coalition government)
            margin = 0 - simple_majority
            parti_mandater_count = 0
        else:
            parti_mandater_count = borg_parti_row.iloc[0]['Mandater']
            margin = parti_mandater_count - simple_majority

        flertal_pct = (parti_mandater_count / total * 100).round(1)

        thin_majorities.append({
            'Kommune': kommune,
            'Borgmester': borgmester_navn,
            'Parti': borgmester_parti,
            'Parti Mandater': parti_mandater_count,
            'Total Mandater': total,
            'Margin (over flertal)': margin,
            'Flertal %': flertal_pct
        })

    df_thin = pd.DataFrame(thin_majorities)
    df_thin = df_thin.sort_values('Margin (over flertal)')

    if len(df_thin) > 0:
        thinnest = df_thin.iloc[0]
        print(f"    → Tyndeste flertal: {thinnest['Kommune']} ({thinnest['Borgmester']}, {thinnest['Parti']}) - margin: {thinnest['Margin (over flertal)']:.1f} mandater")

    return df_thin


def lav_magtanalyse(output_dir='excel_output'):
    """Main analyse funktion"""
    print("🔍 Starter magtanalyse...")

    # Find filer
    parquet_dir = Path(output_dir) / 'parquet'
    samlet_dir = Path(output_dir) / '03_Samlet_Alle_Valg'

    # Valgresultater
    res_fil = find_latest_file(str(parquet_dir / 'valgresultater_ALLE_VALG_*.parquet'))
    if not res_fil:
        res_fil = find_latest_file(str(samlet_dir / 'valgresultater_ALLE_VALG_*.xlsx'))

    # Mandatfordeling
    mand_fil = find_latest_file(str(parquet_dir / 'mandatfordeling_ALLE_VALG_*.parquet'))
    if not mand_fil:
        mand_fil = find_latest_file(str(samlet_dir / 'mandatfordeling_ALLE_VALG_*.xlsx'))

    if not res_fil or not mand_fil:
        print("❌ Mangler nødvendige filer")
        return False

    # Load data
    print(f"📖 Læser data...")
    if res_fil.endswith('.parquet'):
        df_res = load_parquet(res_fil)
    else:
        df_res = pd.read_excel(res_fil)

    if mand_fil.endswith('.parquet'):
        df_mand = load_parquet(mand_fil)
    else:
        df_mand = pd.read_excel(mand_fil)

    # Run all 4 analyses
    df_robbed = find_mandate_theft(df_res, df_mand)
    df_dependency = find_one_person_armies(df_res)
    df_strongholds = find_geographic_strongholds(df_res)
    df_thin = find_thin_majorities(df_mand, output_dir)

    # Save to Excel
    output_file = Path(output_dir) / '00_START_HER' / 'Analyse_magt.xlsx'
    output_file.parent.mkdir(parents=True, exist_ok=True)

    writer = pd.ExcelWriter(output_file, engine='openpyxl')

    # Always write all sheets, even if empty (so generate_findings can load them)
    df_robbed.to_excel(writer, sheet_name='De Tragiske Helte', index=False)
    df_dependency.to_excel(writer, sheet_name='Enmandshæren', index=False)
    df_strongholds.to_excel(writer, sheet_name='Geografiske Højborge', index=False)
    df_thin.to_excel(writer, sheet_name='Tynde Flertaller', index=False)

    writer.close()

    print(f"✅ Magtanalyse gemt: {output_file}")
    return True


def main(output_dir='excel_output'):
    """Main funktion til brug i pipeline"""
    success = lav_magtanalyse(output_dir)
    return success


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Lav magtanalyse')
    parser.add_argument('--output-dir', default='excel_output', help='Output directory')
    args = parser.parse_args()

    success = main(args.output_dir)
    sys.exit(0 if success else 1)
