#!/usr/bin/env python3
"""
Konvertering af valg.dk JSON-filer til Excel
Håndterer nested JSON-strukturer fra SFTP-serveren

Brug: python valg_json_til_excel.py <json_mappe> <output_mappe>
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys
from utils import estimér_køn, save_parquet


def dedupliker_nyeste_data(data_list, gruppering_kolonner):
    """
    Filtrer data til kun at indeholde den nyeste opdatering for hver gruppe.

    Args:
        data_list: Liste af dictionaries med valgdata
        gruppering_kolonner: Liste af kolonnenavne at gruppere på (typisk afstemningsområde + kandidat)

    Returns:
        Liste med kun nyeste data for hver gruppe
    """
    if not data_list:
        return data_list

    # Konverter til DataFrame for lettere manipulation
    df = pd.DataFrame(data_list)

    # Tjek om FrigivelsesTidspunkt findes
    if 'FrigivelsesTidspunkt' not in df.columns:
        return data_list  # Ingen deduplicering mulig

    # Tjek at alle gruppering_kolonner findes
    manglende = [col for col in gruppering_kolonner if col not in df.columns]
    if manglende:
        print(f"  ⚠️  Advarsel: Manglende kolonner for deduplicering: {manglende}")
        return data_list

    # Konverter FrigivelsesTidspunkt til datetime hvis det er en string
    df['FrigivelsesTidspunkt'] = pd.to_datetime(df['FrigivelsesTidspunkt'], errors='coerce')

    # Sorter efter FrigivelsesTidspunkt (nyeste først) og behold kun første række per gruppe
    df_sorted = df.sort_values('FrigivelsesTidspunkt', ascending=False)
    df_deduplicated = df_sorted.drop_duplicates(subset=gruppering_kolonner, keep='first')

    # Konverter tilbage til liste af dictionaries
    return df_deduplicated.to_dict('records')

def fladgør_kandidatdata_kvrv(json_data):
    """
    Fladgør kandidatdata for kommunal/regionsrådsvalg.
    Returnerer liste af kandidater med alle relevante felter.
    Håndterer både gammel og ny JSON-struktur fra valg.dk.
    """
    kandidater = []

    # Tjek om det er den nye struktur (direkte felter) eller gammel (nested under "Valg")
    if "Valgart" in json_data:
        # NY STRUKTUR fra valg.dk 2025

        # Skip data fra tidligere valg (kun 2025 data)
        valgdag = json_data.get("Valgdag", "")
        if valgdag and "-2025" not in valgdag:
            return []  # Spring over data fra tidligere valg

        valg_info = {
            "ValgId": json_data.get("KommuneDagiId") or json_data.get("RegionDagiId") or None,
            "ValgNavn": json_data.get("Valgart", ""),
            "ValgDato": valgdag,
            "KommuneKode": json_data.get("KommuneDagiId") or None,
            "KommuneNavn": json_data.get("Kommune", ""),
            "RegionKode": json_data.get("RegionDagiId") or None,
            "RegionNavn": json_data.get("Region", ""),
            "FrigivelsesTidspunkt": json_data.get("FrigivelsesTidspunktUTC", ""),
            "OpdateringsTidspunkt": json_data.get("OpdateringsTidspunktUTC", ""),
        }

        kandidatlister = json_data.get("Kandidatlister", [])

        for liste in kandidatlister:
            liste_info = {
                "ListeBogstav": liste.get("Bogstavbetegnelse", ""),
                "ListeNavn": liste.get("Navn", ""),
                "ListeId": liste.get("KandidatlisteId", ""),
                "Stemmeseddelplacering": liste.get("Stemmeseddelsplacering", ""),
                "Opstillingsform": liste.get("Opstillingsform", ""),
            }

            for kandidat in liste.get("Kandidater", []):
                # Navn kan være helt navn eller opdelt
                navn = kandidat.get("Navn", "")
                stemmeseddelnavn = kandidat.get("Stemmeseddelnavn", navn)

                if " " in navn:
                    dele = navn.split(" ", 1)
                    fornavn = dele[0]
                    efternavn = dele[1] if len(dele) > 1 else ""
                else:
                    fornavn = navn
                    efternavn = ""

                # Estimér køn
                estimeret_køn, køns_metode = estimér_køn(fornavn)

                row = {
                    **valg_info,
                    **liste_info,
                    "KandidatId": kandidat.get("Id", ""),
                    "Navn": navn,
                    "Stemmeseddelnavn": stemmeseddelnavn,
                    "Fornavn": fornavn,
                    "Efternavn": efternavn,
                    "EstimeretKøn": estimeret_køn,
                    "KønsMetode": køns_metode,
                    "Stilling": kandidat.get("Stilling", ""),
                    "Bopæl": kandidat.get("BopaelPaaStemmeseddel", ""),
                    "KandidatPlacering": kandidat.get("Stemmeseddelsplacering", ""),
                }
                kandidater.append(row)
    else:
        # GAMMEL STRUKTUR (fallback)
        valg = json_data.get("Valg", json_data)
        valg_info = {
            "ValgId": valg.get("Id", ""),
            "ValgNavn": valg.get("Navn", ""),
            "ValgDato": valg.get("Dato", ""),
            "KommuneKode": valg.get("KommuneReference", {}).get("Kode") or None,
            "KommuneNavn": valg.get("KommuneReference", {}).get("Navn", ""),
            "RegionKode": valg.get("RegionReference", {}).get("Kode") or None,
            "RegionNavn": valg.get("RegionReference", {}).get("Navn", ""),
        }

        kandidatlister = valg.get("Kandidatlister", [])

        for liste in kandidatlister:
            liste_info = {
                "ListeBogstav": liste.get("Bogstav", ""),
                "ListeNavn": liste.get("Navn", ""),
                "ListeId": liste.get("Id", ""),
                "Stemmeseddelplacering": liste.get("Stemmeseddelplacering", ""),
            }

            for kandidat in liste.get("Kandidater", []):
                fornavn = kandidat.get("Fornavn", "")

                # Estimér køn
                estimeret_køn, køns_metode = estimér_køn(fornavn)

                row = {
                    **valg_info,
                    **liste_info,
                    "KandidatId": kandidat.get("Id", ""),
                    "Fornavn": fornavn,
                    "Efternavn": kandidat.get("Efternavn", ""),
                    "EstimeretKøn": estimeret_køn,
                    "KønsMetode": køns_metode,
                    "Stilling": kandidat.get("Stilling", ""),
                    "Bopæl": kandidat.get("Bopæl", ""),
                    "KandidatPlacering": kandidat.get("Placering", ""),
                }
                kandidater.append(row)

    return kandidater


def fladgør_valgresultater_kvrv(json_data):
    """
    Fladgør valgresultater for kommunal/regionsrådsvalg.
    Returnerer liste af resultater på kandidat-niveau.
    """
    resultater = []

    # Håndter både ny struktur (direkte felter) og gammel (nested under "Valgresultater")
    if "Valgart" in json_data:
        # NY STRUKTUR 2025
        # Skip data fra tidligere valg (kun 2025 data)
        valgdag = json_data.get("Valgdag", "")
        if valgdag and "-2025" not in valgdag:
            return []  # Spring over data fra tidligere valg

        valg = json_data
    else:
        valg = json_data.get("Valgresultater", json_data)

    # Grundlæggende info om afstemningsområdet
    stemmeberettigede = valg.get("AntalStemmeberettigedeVælgere", valg.get("Stemmeberettigede", 0))
    afgivne_stemmer = valg.get("AfgivneStemmer", 0)
    gyldige_stemmer = valg.get("GyldigeStemmer", 0)
    ugyldige_stemmer = valg.get("UgyldigeStemmerUdoverBlanke", valg.get("UgyldigeStemmer", 0))
    blanke_stemmer = (valg.get("BlankeUgyldigeFremmødteStemmer", 0) +
                     valg.get("BlankeUgyldigeBrevstemmer", 0)) or valg.get("BlankeStemmer", 0)

    # Beregn valgdeltagelse
    valgdeltagelse_pct = (afgivne_stemmer / stemmeberettigede * 100) if stemmeberettigede > 0 else 0
    gyldige_pct = (gyldige_stemmer / afgivne_stemmer * 100) if afgivne_stemmer > 0 else 0

    valg_info = {
        "Valgart": valg.get("Valgart", valg.get("ValgNavn", "")),
        "Valgdag": valg.get("Valgdag", valg.get("ValgDato", "")),
        "AfstemningsområdeDagiId": valg.get("AfstemningsområdeDagiId", ""),
        "AfstemningsområdeNummer": valg.get("AfstemningsområdeNummer", valg.get("AfstemningsområdeReference", {}).get("Nummer", "")),
        "Afstemningsområde": valg.get("Afstemningsområde", valg.get("AfstemningsområdeReference", {}).get("Navn", "")),
        "Kommune": valg.get("Kommune", valg.get("KommuneReference", {}).get("Navn", "")),
        "Kommunekode": valg.get("Kommunekode", valg.get("KommuneReference", {}).get("Kode")) or None,
        "Stemmeberettigede": stemmeberettigede,
        "AfgivneStemmer": afgivne_stemmer,
        "GyldigeStemmer": gyldige_stemmer,
        "UgyldigeStemmer": ugyldige_stemmer,
        "BlankeStemmer": blanke_stemmer,
        "ValgdeltagelseProcent": round(valgdeltagelse_pct, 2),
        "GyldigeProcent": round(gyldige_pct, 2),
        "Resultatart": valg.get("Resultatart", ""),
        "GodkendelsesDato": valg.get("GodkendelsesDatoUTC", ""),
        "FrigivelsesTidspunkt": valg.get("FrigivelsesTidspunktUTC", ""),
        "AfgivneStemmerÆndring": valg.get("AfgivneStemmerDifferenceFraForrigeValg", ""),
        "GyldigeStemmerÆndring": valg.get("GyldigeStemmerDifferenceFraForrigeValg", ""),
        "StemmeberettigedeÆndring": valg.get("AntalStemmeberettigedeVælgereDifferenceFraForrigeValg", ""),
    }

    # Hent kandidatlister med stemmer
    for liste in valg.get("Kandidatlister", []):
        liste_stemmer = liste.get("Stemmer", 0)
        stemmer_ændring = liste.get("StemmerDifferenceFraForrigeValg", "")

        liste_info = {
            "ListeBogstav": liste.get("Bogstavbetegnelse", liste.get("Bogstav", "")),
            "ListeNavn": liste.get("Navn", ""),
            "ListeId": liste.get("KandidatlisteId", liste.get("Id", "")),
            "ListeStemmer": liste_stemmer,
            "ListeStemmerÆndring": stemmer_ændring,
            "Listestemmer": liste.get("Listestemmer", 0),
        }

        # Hent kandidater med personlige stemmer
        for kandidat in liste.get("Kandidater", []):
            personlige_stemmer = kandidat.get("Stemmer", kandidat.get("PersonligeStemmer", 0))

            # Beregn personlig stemmeandel
            personlig_andel_pct = (personlige_stemmer / liste_stemmer * 100) if liste_stemmer > 0 else 0

            row = {
                **valg_info,
                **liste_info,
                "KandidatId": kandidat.get("Id", ""),
                "Stemmeseddelnavn": kandidat.get("Stemmeseddelnavn", ""),
                "PersonligeStemmer": personlige_stemmer,
                "PersonligStemmeAndelProcent": round(personlig_andel_pct, 2),
            }
            resultater.append(row)

    return resultater


def fladgør_mandatfordeling(json_data):
    """
    Fladgør mandatfordeling for kommunal/regionsrådsvalg.
    Inkluderer både valgte kandidater og stedfortrædere.
    """
    mandater = []

    # Håndter både ny og gammel struktur
    if "Valgart" in json_data:
        # NY STRUKTUR 2025
        # Skip data fra tidligere valg (kun 2025 data)
        valgdag = json_data.get("Valgdag", "")
        if valgdag and "-2025" not in valgdag:
            return []  # Spring over data fra tidligere valg

        valg_info = {
            "Valgart": json_data.get("Valgart", ""),
            "Valgdag": valgdag,
            "KommuneKode": json_data.get("Kommunekode") or None,
            "Kommune": json_data.get("Kommune", ""),
            "Resultatart": json_data.get("Resultatart", ""),
            "FrigivelsesTidspunkt": json_data.get("FrigivelsesTidspunktUTC", ""),
        }
    else:
        valg = json_data.get("Valg", json_data)
        valg_info = {
            "ValgId": valg.get("Id", ""),
            "KommuneKode": valg.get("KommuneReference", {}).get("Kode") or None,
            "Kommune": valg.get("KommuneReference", {}).get("Navn", ""),
        }

    # Personlige mandater
    for mandat in json_data.get("PersonligeMandater", []):
        # Ny struktur
        if "KandidatId" in mandat:
            row = {
                **valg_info,
                "MandatType": "Personligt",
                "MandatNummer": mandat.get("Nummer", mandat.get("MandatNummer", "")),
                "NummerAnførtPåListen": mandat.get("NummerAnførtPåListen", ""),
                "KandidatId": mandat.get("KandidatId", ""),
                "Stemmeseddelnavn": mandat.get("Stemmeseddelnavn", ""),
                "ListeId": mandat.get("KandidatlisteId", ""),
                "ListeNavn": mandat.get("KandidatlisteNavn", ""),
                "ListeBogstav": mandat.get("Bogstavbetegnelse", ""),
            }
        else:
            # Gammel struktur
            row = {
                **valg_info,
                "MandatType": "Personligt",
                "MandatNummer": mandat.get("MandatNummer", ""),
                "KandidatId": mandat.get("KandidatReference", {}).get("Id", ""),
                "Fornavn": mandat.get("KandidatReference", {}).get("Fornavn", ""),
                "Efternavn": mandat.get("KandidatReference", {}).get("Efternavn", ""),
            }
        mandater.append(row)

    # Listemandater
    for mandat in json_data.get("ListeMandater", []):
        # Ny struktur
        if "KandidatlisteId" in mandat or "Bogstavbetegnelse" in mandat:
            row = {
                **valg_info,
                "MandatType": "Liste",
                "MandatNummer": mandat.get("Nummer", mandat.get("MandatNummer", "")),
                "ListeId": mandat.get("KandidatlisteId", ""),
                "ListeBogstav": mandat.get("Bogstavbetegnelse", ""),
                "ListeNavn": mandat.get("KandidatlisteNavn", ""),
            }
        else:
            # Gammel struktur
            row = {
                **valg_info,
                "MandatType": "Liste",
                "MandatNummer": mandat.get("MandatNummer", ""),
                "ListeId": mandat.get("KandidatlisteReference", {}).get("Id", ""),
                "ListeBogstav": mandat.get("KandidatlisteReference", {}).get("Bogstav", ""),
                "ListeNavn": mandat.get("KandidatlisteReference", {}).get("Navn", ""),
            }
        mandater.append(row)

    # Stedfortrædere (suppleanter) - kun i ny struktur
    for kandidatliste in json_data.get("Kandidatliste", []):
        liste_info = {
            "ListeId": kandidatliste.get("KandidatlisteId", ""),
            "ListeNavn": kandidatliste.get("KandidatlisteNavn", ""),
            "ListeBogstav": kandidatliste.get("Bogstavbetegnelse", ""),
        }

        for stedfortræder in kandidatliste.get("Stedfortrædere", []):
            row = {
                **valg_info,
                **liste_info,
                "MandatType": "Stedfortræder",
                "StedfortræderNummer": stedfortræder.get("Nummer", ""),
                "KandidatId": stedfortræder.get("KandidatId", ""),
                "Stemmeseddelnavn": stedfortræder.get("Stemmeseddelnavn", ""),
            }
            mandater.append(row)

    return mandater


def process_json_files(json_mappe, output_mappe):
    """
    Hovedfunktion: Læser alle JSON-filer og konverterer til Excel.
    """
    json_mappe = Path(json_mappe)
    output_mappe = Path(output_mappe)
    output_mappe.mkdir(exist_ok=True)

    # Saml data i kategorier - både samlet og opdelt
    alle_kandidater = []
    alle_resultater = []
    alle_mandater = []

    kommunal_kandidater = []
    kommunal_resultater = []
    kommunal_mandater = []

    regions_kandidater = []
    regions_resultater = []
    regions_mandater = []

    # Find alle JSON-filer
    json_filer = list(json_mappe.rglob("*.json"))
    print(f"Fundet {len(json_filer)} JSON-filer i {json_mappe}")

    if not json_filer:
        print("ADVARSEL: Ingen JSON-filer fundet!")
        return
    
    for json_fil in json_filer:
        # Spring over verifikationsdata (testdata fra KOMBIT)
        if 'verifikation' in str(json_fil):
            print(f"Springer over verifikationsdata: {json_fil.name}")
            continue

        print(f"Behandler: {json_fil.name}")

        try:
            # Læs JSON med UTF-8 encoding og håndter BOM
            with open(json_fil, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
            
            filnavn = json_fil.name.lower()
            
            # Kategoriser og fladgør baseret på filtype
            er_kommunal = "kommunalvalg" in filnavn
            er_regions = "regionsrådsvalg" in filnavn or "region" in filnavn

            if "kandidat-data" in filnavn:
                if "kommunalvalg" in filnavn or "regionsrådsvalg" in filnavn:
                    kandidater = fladgør_kandidatdata_kvrv(data)
                    alle_kandidater.extend(kandidater)

                    if er_kommunal:
                        kommunal_kandidater.extend(kandidater)
                    if er_regions:
                        regions_kandidater.extend(kandidater)

                    print(f"  → {len(kandidater)} kandidater")

            elif "valgresultater" in filnavn:
                if "kommunalvalg" in filnavn or "regionsrådsvalg" in filnavn or "kvrv" in filnavn.lower():
                    resultater = fladgør_valgresultater_kvrv(data)
                    alle_resultater.extend(resultater)

                    if er_kommunal:
                        kommunal_resultater.extend(resultater)
                    if er_regions:
                        regions_resultater.extend(resultater)

                    print(f"  → {len(resultater)} resultatrækker")

            elif "mandatfordeling" in filnavn:
                mandater = fladgør_mandatfordeling(data)
                alle_mandater.extend(mandater)

                if er_kommunal:
                    kommunal_mandater.extend(mandater)
                if er_regions:
                    regions_mandater.extend(mandater)

                print(f"  → {len(mandater)} mandater")
            
            else:
                # Generisk håndtering - prøv at flade JSON ud
                if isinstance(data, list):
                    df = pd.json_normalize(data)
                else:
                    df = pd.json_normalize([data])
                
                output_fil = output_mappe / f"{json_fil.stem}.xlsx"
                df.to_excel(output_fil, index=False)
                print(f"  → Gemt som {output_fil.name}")
        
        except json.JSONDecodeError as e:
            print(f"  ✗ JSON-fejl: {e}")
        except Exception as e:
            print(f"  ✗ Fejl: {e}")
    
    # Gem samlede data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    
    # Opret parquet mappe
    parquet_dir = output_mappe / 'parquet'
    parquet_dir.mkdir(exist_ok=True)

    print("\n" + "=" * 60)
    print("GEMMER PARQUET OG EXCEL-FILER")
    print("=" * 60)

    # SAMLEDE FILER (kommunal + regional)
    if alle_kandidater:
        df = pd.DataFrame(alle_kandidater)
        
        # Gem Parquet (primær, hurtig)
        parquet_fil = parquet_dir / f"kandidater_ALLE_VALG_{timestamp}.parquet"
        save_parquet(df, parquet_fil, "Alle kandidater (Parquet)")
        
        # Gem Excel (sekundær, kompatibilitet)
        output_fil = output_mappe / f"kandidater_ALLE_VALG_{timestamp}.xlsx"
        df.to_excel(output_fil, index=False, engine='openpyxl')
        print(f"✓ Alle kandidater (Excel): {output_fil.name}")
        print(f"  {len(alle_kandidater)} rækker, {len(df.columns)} kolonner")

    if alle_resultater:
        # Dedupliker: Behold kun nyeste data per afstemningsområde+kandidat
        print("\n🔄 Deduplikerer valgresultater (beholder kun nyeste opdateringer)...")
        før_antal = len(alle_resultater)
        alle_resultater = dedupliker_nyeste_data(
            alle_resultater,
            ['AfstemningsområdeDagiId', 'KandidatId']
        )
        efter_antal = len(alle_resultater)
        print(f"   Før: {før_antal} rækker → Efter: {efter_antal} rækker ({før_antal - efter_antal} duplikater fjernet)")

        df = pd.DataFrame(alle_resultater)

        # Gem Parquet
        parquet_fil = parquet_dir / f"valgresultater_ALLE_VALG_{timestamp}.parquet"
        save_parquet(df, parquet_fil, "Alle valgresultater (Parquet)")
        
        # Gem Excel
        output_fil = output_mappe / f"valgresultater_ALLE_VALG_{timestamp}.xlsx"
        df.to_excel(output_fil, index=False, engine='openpyxl')
        print(f"✓ Alle valgresultater (Excel): {output_fil.name}")
        print(f"  {len(alle_resultater)} rækker, {len(df.columns)} kolonner")

        # Lav pivottabeller med korrekte resultater pr. kommune/region
        # VIGTIGT: Skal bruge ListeStemmer (total per område) og adskille kommunal/regional
        if 'Kommune' in df.columns and 'ListeNavn' in df.columns and 'ListeStemmer' in df.columns:
            # Først: Dedupliker til én række per afstemningsområde + parti
            # (fordi ListeStemmer er den samme for alle kandidater i et område)
            df_areas = df.groupby(['Valgart', 'Kommune', 'ListeNavn', 'AfstemningsområdeDagiId'])['ListeStemmer'].first().reset_index()

            # Derefter: Summér på tværs af afstemningsområder for hver kommune + parti
            pivot = df_areas.groupby(['Valgart', 'Kommune', 'ListeNavn'])['ListeStemmer'].sum().reset_index()
            pivot.rename(columns={'ListeStemmer': 'TotalStemmer'}, inplace=True)

            # Gem separate filer for kommunalvalg og regionsrådsvalg
            for valgart in pivot['Valgart'].unique():
                valgart_pivot = pivot[pivot['Valgart'] == valgart].copy()
                valgart_pivot = valgart_pivot[['Kommune', 'ListeNavn', 'TotalStemmer']]  # Drop Valgart kolonne

                valgart_navn = valgart.replace('valg', '').replace('råds', 'raads')  # Filvenlig navn
                pivot_fil = output_mappe / f"resultater_per_kommune_{valgart_navn}_{timestamp}.xlsx"
                valgart_pivot.to_excel(pivot_fil, index=False, engine='openpyxl')
                print(f"✓ Pivottabel gemt: {pivot_fil.name} ({len(valgart_pivot)} rækker)")

    if alle_mandater:
        # Dedupliker: Behold kun nyeste data per kandidat
        print("\n🔄 Deduplikerer mandatfordeling (beholder kun nyeste opdateringer)...")
        før_antal = len(alle_mandater)
        alle_mandater = dedupliker_nyeste_data(
            alle_mandater,
            ['KommuneKode', 'KandidatId']
        )
        efter_antal = len(alle_mandater)
        print(f"   Før: {før_antal} rækker → Efter: {efter_antal} rækker ({før_antal - efter_antal} duplikater fjernet)")

        df = pd.DataFrame(alle_mandater)

        # Gem Parquet
        parquet_fil = parquet_dir / f"mandatfordeling_ALLE_VALG_{timestamp}.parquet"
        save_parquet(df, parquet_fil, "Alle mandater (Parquet)")
        
        # Gem Excel
        output_fil = output_mappe / f"mandatfordeling_ALLE_VALG_{timestamp}.xlsx"
        df.to_excel(output_fil, index=False, engine='openpyxl')
        print(f"✓ Alle mandater (Excel): {output_fil.name}")
        print(f"  {len(alle_mandater)} rækker")

    # SEPARATE FILER FOR KOMMUNALVALG
    print("\n" + "-" * 60)
    print("KOMMUNALVALG")
    print("-" * 60)

    if kommunal_kandidater:
        df = pd.DataFrame(kommunal_kandidater)
        
        # Gem Parquet
        parquet_fil = parquet_dir / f"kandidater_KOMMUNAL_{timestamp}.parquet"
        save_parquet(df, parquet_fil, "Kommunale kandidater (Parquet)")
        
        # Gem Excel
        output_fil = output_mappe / f"kandidater_KOMMUNAL_{timestamp}.xlsx"
        df.to_excel(output_fil, index=False, engine='openpyxl')
        print(f"✓ Kommunale kandidater (Excel): {output_fil.name}")
        print(f"  {len(kommunal_kandidater)} rækker, {len(df.columns)} kolonner")

    if kommunal_resultater:
        # Dedupliker: Behold kun nyeste data per afstemningsområde+kandidat
        print("\n🔄 Deduplikerer kommunale valgresultater...")
        før_antal = len(kommunal_resultater)
        kommunal_resultater = dedupliker_nyeste_data(
            kommunal_resultater,
            ['AfstemningsområdeDagiId', 'KandidatId']
        )
        efter_antal = len(kommunal_resultater)
        print(f"   Før: {før_antal} rækker → Efter: {efter_antal} rækker ({før_antal - efter_antal} duplikater fjernet)")

        df = pd.DataFrame(kommunal_resultater)

        # Gem Parquet
        parquet_fil = parquet_dir / f"valgresultater_KOMMUNAL_{timestamp}.parquet"
        save_parquet(df, parquet_fil, "Kommunale resultater (Parquet)")
        
        # Gem Excel
        output_fil = output_mappe / f"valgresultater_KOMMUNAL_{timestamp}.xlsx"
        df.to_excel(output_fil, index=False, engine='openpyxl')
        print(f"✓ Kommunale resultater (Excel): {output_fil.name}")
        print(f"  {len(kommunal_resultater)} rækker, {len(df.columns)} kolonner")

    if kommunal_mandater:
        # Dedupliker: Behold kun nyeste data per kandidat
        print("\n🔄 Deduplikerer kommunale mandater...")
        før_antal = len(kommunal_mandater)
        kommunal_mandater = dedupliker_nyeste_data(
            kommunal_mandater,
            ['KommuneKode', 'KandidatId']
        )
        efter_antal = len(kommunal_mandater)
        print(f"   Før: {før_antal} rækker → Efter: {efter_antal} rækker ({før_antal - efter_antal} duplikater fjernet)")

        df = pd.DataFrame(kommunal_mandater)

        # Gem Parquet
        parquet_fil = parquet_dir / f"mandatfordeling_KOMMUNAL_{timestamp}.parquet"
        save_parquet(df, parquet_fil, "Kommunale mandater (Parquet)")
        
        # Gem Excel
        output_fil = output_mappe / f"mandatfordeling_KOMMUNAL_{timestamp}.xlsx"
        df.to_excel(output_fil, index=False, engine='openpyxl')
        print(f"✓ Kommunale mandater (Excel): {output_fil.name}")
        print(f"  {len(kommunal_mandater)} rækker")

    # SEPARATE FILER FOR REGIONSRÅDSVALG
    print("\n" + "-" * 60)
    print("REGIONSRÅDSVALG")
    print("-" * 60)

    if regions_kandidater:
        df = pd.DataFrame(regions_kandidater)
        
        # Gem Parquet
        parquet_fil = parquet_dir / f"kandidater_REGIONAL_{timestamp}.parquet"
        save_parquet(df, parquet_fil, "Regionale kandidater (Parquet)")
        
        # Gem Excel
        output_fil = output_mappe / f"kandidater_REGIONAL_{timestamp}.xlsx"
        df.to_excel(output_fil, index=False, engine='openpyxl')
        print(f"✓ Regionale kandidater (Excel): {output_fil.name}")
        print(f"  {len(regions_kandidater)} rækker, {len(df.columns)} kolonner")

    if regions_resultater:
        # Dedupliker: Behold kun nyeste data per afstemningsområde+kandidat
        print("\n🔄 Deduplikerer regionale valgresultater...")
        før_antal = len(regions_resultater)
        regions_resultater = dedupliker_nyeste_data(
            regions_resultater,
            ['AfstemningsområdeDagiId', 'KandidatId']
        )
        efter_antal = len(regions_resultater)
        print(f"   Før: {før_antal} rækker → Efter: {efter_antal} rækker ({før_antal - efter_antal} duplikater fjernet)")

        df = pd.DataFrame(regions_resultater)
        
        # Gem Parquet
        parquet_fil = parquet_dir / f"valgresultater_REGIONAL_{timestamp}.parquet"
        save_parquet(df, parquet_fil, "Regionale resultater (Parquet)")
        
        # Gem Excel
        output_fil = output_mappe / f"valgresultater_REGIONAL_{timestamp}.xlsx"
        df.to_excel(output_fil, index=False, engine='openpyxl')
        print(f"✓ Regionale resultater (Excel): {output_fil.name}")
        print(f"  {len(regions_resultater)} rækker, {len(df.columns)} kolonner")

    if regions_mandater:
        # Dedupliker: Behold kun nyeste data per kandidat
        print("\n🔄 Deduplikerer regionale mandater...")
        før_antal = len(regions_mandater)
        regions_mandater = dedupliker_nyeste_data(
            regions_mandater,
            ['KommuneKode', 'KandidatId']
        )
        efter_antal = len(regions_mandater)
        print(f"   Før: {før_antal} rækker → Efter: {efter_antal} rækker ({før_antal - efter_antal} duplikater fjernet)")

        df = pd.DataFrame(regions_mandater)

        # Gem Parquet
        parquet_fil = parquet_dir / f"mandatfordeling_REGIONAL_{timestamp}.parquet"
        save_parquet(df, parquet_fil, "Regionale mandater (Parquet)")
        
        # Gem Excel
        output_fil = output_mappe / f"mandatfordeling_REGIONAL_{timestamp}.xlsx"
        df.to_excel(output_fil, index=False, engine='openpyxl')
        print(f"✓ Regionale mandater (Excel): {output_fil.name}")
        print(f"  {len(regions_mandater)} rækker")

    print("\n" + "=" * 60)
    print(f"✅ KONVERTERING FÆRDIG!")
    print(f"📁 Se alle filer i: {output_mappe}")
    print("=" * 60)


def main(json_mappe=None, output_mappe=None):
    """Main funktion til brug i pipeline"""
    # Hvis ikke angivet, brug sys.argv (for CLI-brug)
    if json_mappe is None:
        if len(sys.argv) < 2:
            print("Brug: python valg_json_til_excel.py <json_mappe> [output_mappe]")
            print("\nEksempel:")
            print('  python valg_json_til_excel.py "C:\\Users\\Nils\\valg_data" "C:\\Users\\Nils\\excel_output"')
            sys.exit(1)
        json_mappe = sys.argv[1]
    
    if output_mappe is None:
        output_mappe = sys.argv[2] if len(sys.argv) > 2 else Path(json_mappe) / "excel_output"
    
    print("=" * 60)
    print("VALG.DK JSON til Excel Konvertering")
    print("=" * 60)
    print(f"JSON-mappe: {json_mappe}")
    print(f"Output-mappe: {output_mappe}")
    print()
    
    process_json_files(json_mappe, output_mappe)


if __name__ == "__main__":
    main()
