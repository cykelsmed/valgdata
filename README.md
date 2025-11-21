# Valgdata 2025 - Automatiseret Pipeline

Komplet automatiseret pipeline til analyse af danske valgdata (Kommunal- og Regionsrådsvalg 2025) med kønsanalyse, stemmeslugere, valgdeltagelse, erhvervsfordeling og geografisk analyse.

## 🎯 Features

- **Automatisk SFTP-download** fra valg.dk's offentlige server
- **JSON til Excel konvertering** med automatisk kønsestimering via fornavne
- **Kønsanalyse** per parti, kommune og region
- **Stemmeslugere-analyse** - Top 100 kandidater med flest personlige stemmer
- **Valgdeltagelse** per kommune og region
- **Erhvervsanalyse** - Job-titler og erhvervsfordeling per parti
- **Partistatistik** - Kandidater, stemmer og gennemsnit
- **Geografisk analyse** - Lokale vs eksterne kandidater
- **Borgmester-analyse** - Partifordeling, magtskifter, kønsfordeling blandt borgmestre
- **Magtanalyse (NYT!)** - Enmandshære, mandattyveri, geografiske højborge, tynde flertaller
- **Auto-genererede findings** i MASTER_FINDINGS.md
- **Komplet pipeline** - én kommando kører alt

## 🚀 Hurtig Start

```bash
# 1. Installer dependencies
pip install -r requirements.txt

# 2. Kør hele pipeline
python pipeline.py --all

# 3. Find resultaterne
cd excel_output/00_START_HER/
```

## 📊 Key Findings (2025)

- **10,365 kandidater** (98 kommuner, 5 regioner)
- **97 borgmestre valgt** - Venstre (42), Socialdemokratiet (22), Konservative (19)
- **57.7% genvalgt** - 30.9% magtskifte, 11.3% nyvalgt
- **Top stemmemagnet:** Anders Winnerskjold (Socialdemokratiet, Aarhus) med 38,064 stemmer
- **Højeste valgdeltagelse:** Fanø & Læsø Kommune (85.7%)
- **Mest almindelige erhverv:** Direktør/Leder (13.2%), Pensionist (11.3%)
- **Kønsfordeling kandidater:** 65.3% mænd, 34.7% kvinder (100% kendt køn!)
- **Kønsfordeling borgmestre:** 74.2% mænd, 25.8% kvinder
- **Bedste kønsbalance:** Alternativet (48.3% kvinder)
- **Flest kandidater:** Socialdemokratiet (1,630 kandidater)
- **Lokale kandidater:** 22.5% bor i samme kommune som de stiller op i

## 📁 Pipeline Outputs

### Start her (små filer i `00_START_HER/`):
1. **MASTER_FINDINGS.md** - Komplet overblik over alle findings (stemmeslugere, valgdeltagelse, køn, erhverv, borgmestre, magtanalyse)
2. **Analyse_magt.xlsx** (25 KB) - **NYT!** Enmandshære, mandattyveri, geografiske højborge, tynde flertaller
3. **Analyse_generel.xlsx** (38 KB) - TOP 100 stemmeslugere, valgdeltagelse, job-titler, partistatistik
4. **Analyse_borgmestre.xlsx** (13 KB) - 97 borgmestre, partifordeling, magtskifter, kønsfordeling
5. **Analyse_kønsfordeling.xlsx** (16 KB) - Kønsfordeling per parti/kommune/region

### Detaljerede data:
- **01_Kommunalvalg/** - Alle kommunale data (~59 MB)
- **02_Regionsrådsvalg/** - Alle regionale data (~130 MB)
- **03_Samlet_Alle_Valg/** - Kombineret datasæt (~200 MB)
- **04_Reference_Geografi/** - Geografiske reference-filer (~196 KB)
- **05_Valgdeltagelse_Kommunal/** - 1,283 valgdeltagelse-filer per opstillingskreds (~10 MB)
- **06_Valgdeltagelse_Regional/** - 1,223 valgdeltagelse-filer per opstillingskreds (~9.6 MB)

## 🛠️ Scripts

| Script | Beskrivelse |
|--------|-------------|
| `pipeline.py` | Central orchestrator - kør med `--all` |
| `hent_valgdata.py` | Download fra valg.dk SFTP |
| `valg_json_til_excel.py` | JSON → Excel med kønsestimering |
| `lav_kønsanalyse.py` | Generer kønsanalyse per parti/kommune |
| `lav_generel_analyse.py` | Generel analyse (valgdeltagelse, job, stemmeslugere, partistatistik) |
| `parse_borgmestre.py` | Parse borgmestre.md til struktureret CSV |
| `lav_borgmester_analyse.py` | Borgmester-analyse (partifordeling, magtskifter, køn) |
| `lav_magtanalyse.py` | **NYT!** Magtanalyse (enmandshære, mandattyveri, højborge, tynde flertaller) |
| `generate_findings.py` | Auto-generer MASTER_FINDINGS.md |
| `validate_data.py` | Valider data for fejl og realistiske værdier |
| `validate_aggregates.py` | Valider nationale totaler og intern konsistens mod DR/valg.dk |
| `stikprøve_validering.py` | Spot-check validering af specifikke kommune+parti kombinationer |
| `tjek_tommy_problemer.py` | Specifik validering af rapporterede dataudfordringer |

## 📋 Pipeline Options

```bash
# Kør hele pipeline
python pipeline.py --all

# Kun konvertering (hvis JSON allerede downloadet)
python pipeline.py --skip-download --all

# Kun specifikke trin
python pipeline.py --download          # Kun download
python pipeline.py --convert           # Kun konvertering
python pipeline.py --analyze           # Kun kønsanalyse
python pipeline.py --findings          # Kun findings

# Slet gamle filer og kør forfra
python pipeline.py --clean --all
```

## 🔍 Datasæt

### Kandidater
Alle felter fra valg.dk plus kønsestimering:
- ValgNavn, ValgDato, KommuneNavn, RegionNavn
- ListeBogstav, ListeNavn, Stemmeseddelplacering
- Navn, Fornavn, Efternavn, **EstimeretKøn**
- Stilling, Bopæl, KandidatPlacering

### Valgresultater (efter valget)
- Personlige stemmer per kandidat
- Listestemmer per parti
- Mandatfordeling
- Valgdeltagelse per afstemningsområde

### Kønsanalyse
- Kønsfordeling total og per parti
- Bedste/værste kønsbalance
- Regional analyse
- Kønsfordeling blandt valgte vs alle kandidater

## ⚠️ Data Quality

**Styrker:**
- ✅ Officielle data fra valg.dk
- ✅ Komplet dækning (alle 98 kommuner, 5 regioner)
- ✅ Ned til afstemningsområde-niveau
- ✅ 100% kønsbestemmelse via kombineret automatisk + manuel identifikation
- ✅ Verificeret mod testdata - eksklusion af KOMBIT's verifikationsdata

**Begrænsninger:**
- ⚠️ Køn er ESTIMERET via fornavne (ikke officielle data)
- ⚠️ Binær kønsklassifikation (M/K)
- ⚠️ Ingen demografiske data (alder, uddannelse)

**Validering:**
- ✅ **100% match** med DR's officielle nationale totaler (stemmeberettigede, gyldige stemmer, valgdeltagelse)
- ✅ **100% match** på verificerede stikprøver (Hjørring-Venstre: 8,037 stemmer, Hedensted-DF: 1,829 stemmer)
- ✅ **Intern konsistens** verificeret (stemme-balance, ingen duplikater, realistiske værdier)
- ✅ **Pivot-filer opdelt** korrekt per valgtype (kommunal/regional) med korrekt brug af ListeStemmer (personlige + listestemmer)
- ℹ️ Se `VALIDERINGS_RAPPORT.md` for detaljeret valideringsgennemgang

## 🔧 Tekniske Detaljer

### SFTP Download
- **Server:** data.valg.dk:22
- **Login:** Valg / Valg (offentligt tilgængeligt)
- **Output:** ~2,800 JSON-filer

### Kønsestimering
Kombineret automatisk og manuel kønsbestemmelse:
- **gender-guesser library** til automatisk estimering (dansk navnedata)
- **Manuel database** med 810 verificerede navne (fra manuel + AI-identifikation)
- **100% kønsbestemmelse** - ingen ukendte
- Metode markeret i data: "manuel identifikation" eller "gender-guesser"

### Dependencies
```
pandas>=2.0.0
openpyxl>=3.1.0
paramiko>=3.0.0
gender-guesser>=0.4.0
```

## 📈 Mulige Analyser

Med dette datasæt kan du undersøge:

✅ **Kønsfordeling** - Per parti, kommune, region, blandt valgte
✅ **Valgdeltagelse** - Per afstemningsområde, geografiske mønstre (se Analyse_generel.xlsx)
✅ **Personlige mandater** - Top 100 stemmeslugere med flest stemmer (se Analyse_generel.xlsx)
✅ **Erhvervsfordeling** - Kandidaternes job-titler per parti (se Analyse_generel.xlsx)
✅ **Partistatistik** - Kandidater, stemmer og gennemsnit per parti (se Analyse_generel.xlsx)
✅ **Geografiske mønstre** - "Røde" vs "blå" områder, lokale vs udefra kommende kandidater
✅ **Historisk sammenligning** - Ændringer siden 2021 (kræver historiske data)

## 🤝 Bidrag

Forbedringsforslag:
1. Tilføj historisk sammenligning med 2021-data
2. Implementer alder-estimering via CPR (hvis tilgængeligt)
3. Tilføj socioøkonomiske data (kræver ekstra datakilder)
4. Visualiseringer (matplotlib/seaborn)

## 📜 Licens

Fri til brug. Data fra valg.dk er offentligt tilgængelige.

## 📞 Kontakt & Kildeangivelse

**GitHub Repository:** https://github.com/cykelsmed/valgdata

**Data:** Officielle valgresultater fra KOMBIT/valg.dk
**Analyse:** Automatiseret pipeline med pandas/Python

**Ved brug af data:**
Angiv venligst kilde som "Valgdata 2025 analyse (github.com/cykelsmed/valgdata)"

**Spørgsmål:**
- Tekniske spørgsmål: Se GitHub repository
- Officielle valgdata: valg@kombit.dk

---

**⭐ Star projektet på GitHub hvis du bruger dataene!**
