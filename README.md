# Valgdata 2025 - Automatiseret Pipeline

Komplet automatiseret pipeline til analyse af danske valgdata (Kommunal- og Regionsrådsvalg 2025) med kønsanalyse.

## 🎯 Features

- **Automatisk SFTP-download** fra valg.dk's offentlige server
- **JSON til Excel konvertering** med automatisk kønsestimering via fornavne
- **Kønsanalyse** per parti, kommune og region
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
- **Kønsfordeling:** 65.3% mænd, 34.7% kvinder (100% kendt køn!)
- **Bedste kønsbalance:** SF (48.5% kvinder)
- **Lavest andel kvinder:** Liberal Alliance (22.0% kvinder)
- **Flest kandidater:** Socialdemokratiet (1,630 kandidater)

## 📁 Pipeline Outputs

### Start her (små filer i `00_START_HER/`):
1. **MASTER_FINDINGS.md** - Oversigt over alle key findings
2. **Analyse_kønsfordeling.xlsx** (16 KB) - Kønsfordeling per parti/kommune
3. **Analyse_generel.xlsx** (38 KB) - Stemmeslugere, valgdeltagelse, job-titler, geografi
4. **Analyse_eksempel_stemmeslugere.xlsx** (13 KB) - Top 20 stemmeslugere
5. **EXECUTIVE_SUMMARY.txt** - Hurtig tekstoversigt

### Detaljerede data:
- **01_Kommunalvalg/** - Alle kommunale data (~24 MB)
- **02_Regionsrådsvalg/** - Alle regionale data (~61 MB)
- **03_Samlet_Alle_Valg/** - Kombineret datasæt (~83 MB)
- **04_Reference_Geografi/** - Geografiske data

## 🛠️ Scripts

| Script | Beskrivelse |
|--------|-------------|
| `pipeline.py` | Central orchestrator - kør med `--all` |
| `hent_valgdata.py` | Download fra valg.dk SFTP |
| `valg_json_til_excel.py` | JSON → Excel med kønsestimering |
| `lav_kønsanalyse.py` | Generer kønsanalyse per parti/kommune |
| `lav_generel_analyse.py` | Generel analyse (valgdeltagelse, job, stemmeslugere) |
| `generate_findings.py` | Auto-generer MASTER_FINDINGS.md |

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

## 📞 Kontakt

**Spørgsmål til data:** valg@kombit.dk
**Repository:** https://github.com/cykelsmed/valgdata
