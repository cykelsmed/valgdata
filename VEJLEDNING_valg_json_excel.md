# Vejledning: Hent og konverter valg.dk data til Excel

## Oversigt

Dette projekt indeholder to scripts til automatisk at hente valgdata fra valg.dk's SFTP-server og konvertere dem til Excel-format.

**Testet med:** Kommunalvalg og Regionsrådsvalg 2025

## Hurtig start

### 1. Installer Python-biblioteker
```bash
pip install pandas openpyxl paramiko
```

### 2. Hent data fra SFTP
```bash
python hent_valgdata.py ./json_data
```
Dette downloader alle JSON-filer fra valg.dk's SFTP-server (data.valg.dk).

### 3. Konverter til Excel
```bash
python valg_json_til_excel.py ./json_data ./excel_output
```

## Scripts

### `hent_valgdata.py` - Automatisk SFTP-download

Forbinder til valg.dk's offentlige SFTP-server og downloader alle JSON-filer:

- **Server:** data.valg.dk
- **Port:** 22
- **Brugernavn:** Valg
- **Password:** Valg

Scriptet downloader rekursivt alle mapper og bevarer mappestrukturen.

**Eksempel output:**
```
VALG.DK SFTP Download
Forbinder til data.valg.dk...
Forbindelse oprettet!
[MAPPE] kandidat-data/
  ↓ kandidat-data-Kommunalvalg-København-061020251300.json (56.1 KB)
  ↓ kandidat-data-Kommunalvalg-Aarhus-081020250733.json (45.0 KB)
  ...
Total: 2797 JSON-filer hentet
```

### `valg_json_til_excel.py` - JSON til Excel konvertering

Læser alle JSON-filer og samler dem i overskuelige Excel-filer.

**Understøtter:**
- Kandidat-data (kommunal- og regionsrådsvalg)
- Valgresultater (efter valget er afholdt)
- Mandatfordeling
- Valggeografi (kommuner, regioner, afstemningsområder)

## Output-filer

Efter konvertering genereres disse Excel-filer:

| Fil | Indhold | Eksempel |
|-----|---------|----------|
| `kandidater_samlet_[timestamp].xlsx` | Alle kandidater med parti, stilling, bopæl | 10.371 rækker, 19 kolonner |
| `valgresultater_samlet_[timestamp].xlsx` | Stemmer pr. kandidat (efter valget) | - |
| `resultater_per_kommune_[timestamp].xlsx` | Aggregeret pr. kommune/liste | - |
| `mandatfordeling_samlet_[timestamp].xlsx` | Valgte kandidater | - |

### Kandidat-data kolonner:
- ValgId, ValgNavn, ValgDato
- KommuneKode, KommuneNavn
- RegionKode, RegionNavn
- ListeBogstav, ListeNavn, Stemmeseddelplacering
- KandidatId, Navn, Fornavn, Efternavn
- Stilling, Bopæl, KandidatPlacering

## Fejlfinding

### "JSON-fejl: Unexpected character"
Scriptet håndterer automatisk UTF-8 BOM (Byte Order Mark), som er årsagen til fejlen i Excel Power Query.

### "0 resultatrækker"
Normalt fordi valget ikke er afholdt endnu. JSON-filerne indeholder kun skabeloner uden stemmedata før valgdagen.

### Manglende regioner
Tjek at SFTP-download er komplet. Nogle regioner kan mangle fra SFTP-serveren.

## Eksempel: Komplet workflow

```bash
# 1. Opret mappe til data
mkdir json_data excel_output

# 2. Download fra SFTP (tager ca. 2-3 minutter)
python hent_valgdata.py ./json_data

# 3. Konverter til Excel (tager ca. 1-2 minutter for ~3000 filer)
python valg_json_til_excel.py ./json_data ./excel_output

# 4. Åbn resultat
open ./excel_output/kandidater_samlet_*.xlsx
```

## Anbefalinger til KOMBIT/Netcompany

For at gøre data mere tilgængelige:

1. **Tilbyd Excel-eksport** direkte fra valg.dk
2. **Publicér færdige datasæt** på opendata.dk
3. **Inkludér CSV** som alternativ til JSON
4. **Dokumentér JSON Schema** bedre med eksempler
5. **Tilbyd samlet fil** med alle kommuner/regioner

Kontakt: valg@kombit.dk

## Tekniske detaljer

- Python 3.x påkrævet
- Afhængigheder: pandas, openpyxl, paramiko
- Håndterer nested JSON-strukturer automatisk
- UTF-8 encoding med BOM-understøttelse
- Rekursiv SFTP-download

## Licens

Frit til brug. Data fra valg.dk er offentligt tilgængelige.
