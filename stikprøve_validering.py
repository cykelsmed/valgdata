#!/usr/bin/env python3
"""
Stikprøve-validering af valgdata mod valg.dk

Dette script tjekker udvalgte stikprøver for at validere at vores data matcher valg.dk.
"""

import pandas as pd
from pathlib import Path
from utils import find_latest_file, load_parquet

# Stikprøver at tjekke (Kommune, Parti, Forventet total fra valg.dk)
# Værdi = None betyder at den skal valideres manuelt ved at finde tal på valg.dk
# Kilde: https://nyheder.tv2.dk/kommunalvalg/valgresultater/[kommune-navn]

STIKPRØVER = [
    # ============= VERIFICEREDE MATCHES ✅ =============
    ('Hjørring Kommune', 'Venstre, Danmarks Liberale Parti', 8037),
    ('Hedensted Kommune', 'Dansk Folkeparti', 1829),

    # ============= STORE KOMMUNER (>200k indbyggere) =============
    # København
    ('Københavns Kommune', 'Socialdemokratiet', None),
    ('Københavns Kommune', 'Enhedslisten - De Rød-Grønne', None),
    ('Københavns Kommune', 'Det Konservative Folkeparti', None),

    # Aarhus
    ('Aarhus Kommune', 'SF - Socialistisk Folkeparti', None),
    ('Aarhus Kommune', 'Socialdemokratiet', None),
    ('Aarhus Kommune', 'Venstre, Danmarks Liberale Parti', None),

    # Odense
    ('Odense Kommune', 'Socialdemokratiet', None),
    ('Odense Kommune', 'Venstre, Danmarks Liberale Parti', None),
    ('Odense Kommune', 'Det Konservative Folkeparti', None),

    # Aalborg
    ('Aalborg Kommune', 'Venstre, Danmarks Liberale Parti', None),
    ('Aalborg Kommune', 'Socialdemokratiet', None),
    ('Aalborg Kommune', 'SF - Socialistisk Folkeparti', None),

    # ============= MELLEMSTORE KOMMUNER (50k-150k) =============
    ('Randers Kommune', 'Venstre, Danmarks Liberale Parti', None),
    ('Randers Kommune', 'Socialdemokratiet', None),

    ('Horsens Kommune', 'Venstre, Danmarks Liberale Parti', None),
    ('Horsens Kommune', 'Socialdemokratiet', None),

    ('Vejle Kommune', 'Venstre, Danmarks Liberale Parti', None),
    ('Vejle Kommune', 'Det Konservative Folkeparti', None),

    ('Esbjerg Kommune', 'Venstre, Danmarks Liberale Parti', None),
    ('Esbjerg Kommune', 'Socialdemokratiet', None),

    ('Kolding Kommune', 'Venstre, Danmarks Liberale Parti', None),

    # ============= MINDRE KOMMUNER (<20k) =============
    ('Læsø Kommune', 'Venstre, Danmarks Liberale Parti', None),
    ('Fanø Kommune', 'Venstre, Danmarks Liberale Parti', None) if any('Fanø' in k for k in ['Fanø']) else None,
    ('Ærø Kommune', 'Venstre, Danmarks Liberale Parti', None),
    ('Langeland Kommune', 'Socialdemokratiet', None),

    # ============= FORSKELLIGE PARTIER (inklusive lokallister) =============
    # Liberal Alliance
    ('Gentofte Kommune', 'Liberal Alliance', None),

    # Radikale Venstre
    ('Københavns Kommune', 'Radikale Venstre', None),

    # Danmarksdemokraterne
    ('Frederiksberg Kommune', 'Danmarksdemokraterne - Inger Støjberg', None) if any('Frederiksberg' in k for k in ['Frederiksberg']) else None,

    # Lokallister (hvis tilgængelige)
    # ('Kommune med lokalliste', 'Lokalliste navn', None),
]

# Fjern None entries
STIKPRØVER = [s for s in STIKPRØVER if s is not None]

def hent_valgresultater():
    """Find og load den nyeste valgresultater fil"""
    parquet_dir = Path('excel_output/parquet')
    samlet_dir = Path('excel_output/03_Samlet_Alle_Valg')

    res_fil = find_latest_file(str(parquet_dir / 'valgresultater_KOMMUNAL_*.parquet'))
    if not res_fil:
        res_fil = find_latest_file(str(samlet_dir / 'valgresultater_KOMMUNAL_*.xlsx'))
    if not res_fil:
        res_fil = find_latest_file('excel_output/valgresultater_KOMMUNAL_*.xlsx')

    if not res_fil:
        raise FileNotFoundError("Kunne ikke finde valgresultater fil")

    print(f"📖 Læser: {Path(res_fil).name}\n")

    if res_fil.endswith('.parquet'):
        return load_parquet(res_fil)
    else:
        return pd.read_excel(res_fil)

def tjek_stikprøve(df, kommune, liste_navn, forventet_total):
    """Tjek en enkelt stikprøve"""
    # Filtrer data
    filtreret = df[
        (df['Kommune'] == kommune) &
        (df['ListeNavn'] == liste_navn)
    ].copy()

    if len(filtreret) == 0:
        return {
            'status': 'IKKE_FUNDET',
            'fejl': f"Ingen data fundet for {liste_navn} i {kommune}"
        }

    # Beregn totaler
    personlige_stemmer = filtreret['PersonligeStemmer'].sum()

    # Dedupliker listestemmer (én per afstemningsområde)
    liste_dedup = filtreret[['AfstemningsområdeDagiId', 'Listestemmer']].drop_duplicates()
    listestemmer = liste_dedup['Listestemmer'].sum()

    vores_total = personlige_stemmer + listestemmer

    result = {
        'status': 'OK',
        'personlige': personlige_stemmer,
        'liste': listestemmer,
        'vores_total': vores_total,
        'forventet': forventet_total,
        'antal_rækker': len(filtreret),
        'antal_områder': filtreret['AfstemningsområdeDagiId'].nunique(),
        'antal_kandidater': filtreret['KandidatId'].nunique()
    }

    # Tjek mod forventet værdi hvis angivet
    if forventet_total is not None:
        difference = vores_total - forventet_total
        result['difference'] = difference
        result['match'] = (difference == 0)
        result['procent_afvigelse'] = (difference / forventet_total * 100) if forventet_total > 0 else 0

    return result

def print_resultat(kommune, liste_navn, resultat):
    """Print resultat for en stikprøve"""
    print(f"\n{'='*80}")
    print(f"📊 {kommune} - {liste_navn}")
    print(f"{'='*80}")

    if resultat['status'] == 'IKKE_FUNDET':
        print(f"❌ {resultat['fejl']}")
        return

    print(f"   Antal kandidater: {resultat['antal_kandidater']}")
    print(f"   Antal afstemningsområder: {resultat['antal_områder']}")
    print(f"   Antal datarækker: {resultat['antal_rækker']}")
    print(f"\n   Vores data:")
    print(f"      Personlige stemmer: {resultat['personlige']:,}")
    print(f"      Listestemmer:       {resultat['liste']:,}")
    print(f"      Total:              {resultat['vores_total']:,}")

    if resultat['forventet'] is not None:
        print(f"\n   valg.dk:             {resultat['forventet']:,}")
        print(f"   Difference:          {resultat['difference']:,}")

        if resultat['match']:
            print(f"   ✅ PERFEKT MATCH!")
        else:
            procent = abs(resultat['procent_afvigelse'])
            if procent < 0.1:
                print(f"   ⚠️  Lille afvigelse: {resultat['procent_afvigelse']:.2f}%")
            elif procent < 1:
                print(f"   ⚠️  Moderat afvigelse: {resultat['procent_afvigelse']:.2f}%")
            else:
                print(f"   ❌ STOR AFVIGELSE: {resultat['procent_afvigelse']:.2f}%")
    else:
        print(f"\n   ℹ️  Ingen forventet værdi angivet - tilføj værdi fra valg.dk")

def main():
    print("="*80)
    print("STIKPRØVE-VALIDERING AF VALGDATA")
    print("="*80)

    # Load data
    df = hent_valgresultater()

    # Kør stikprøver
    resultater = []
    for kommune, liste_navn, forventet in STIKPRØVER:
        resultat = tjek_stikprøve(df, kommune, liste_navn, forventet)
        print_resultat(kommune, liste_navn, resultat)
        resultater.append({
            'Kommune': kommune,
            'Parti': liste_navn,
            **resultat
        })

    # Sammenfatning
    print(f"\n\n{'='*80}")
    print("📋 SAMMENFATNING")
    print(f"{'='*80}")

    tjekket = sum(1 for r in resultater if r['status'] == 'OK' and r.get('forventet') is not None)
    matches = sum(1 for r in resultater if r.get('match', False))
    ikke_fundet = sum(1 for r in resultater if r['status'] == 'IKKE_FUNDET')
    mangler_værdi = sum(1 for r in resultater if r['status'] == 'OK' and r.get('forventet') is None)

    print(f"   Totalt antal stikprøver: {len(STIKPRØVER)}")
    print(f"   Tjekket mod valg.dk: {tjekket}")
    print(f"   Perfekte matches: {matches}")
    print(f"   Mangler forventet værdi: {mangler_værdi}")
    print(f"   Ikke fundet: {ikke_fundet}")

    if tjekket > 0:
        success_rate = (matches / tjekket * 100)
        print(f"\n   Success rate: {success_rate:.1f}%")

        if success_rate == 100:
            print(f"\n   ✅ ALLE STIKPRØVER MATCHER VALG.DK!")
        elif success_rate >= 90:
            print(f"\n   ⚠️  De fleste stikprøver matcher, men der er nogle afvigelser")
        else:
            print(f"\n   ❌ MANGE AFVIGELSER - undersøg nærmere!")

    print(f"\n{'='*80}\n")

    # Tip til at tilføje flere stikprøver
    if mangler_værdi > 0:
        print("💡 TIP: Tilføj flere stikprøver ved at:")
        print("   1. Besøg valg.dk og find totalen for et parti i en kommune")
        print("   2. Tilføj en linje i STIKPRØVER-listen i dette script")
        print("   3. Kør scriptet igen\n")

if __name__ == '__main__':
    main()
