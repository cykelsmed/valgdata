# Refactor Valgdata Codebase til Professionel Standard

**Dato:** 20. november 2025  
**Status:** Planlagt (ikke implementeret)

## Oversigt

Løft valgdata-projektet fra hobby-niveau til professionelt setup med Parquet for interne mellemregninger, DRY-principper via utils.py, eksternalisering af kønsdata til JSON, og robust SFTP-download med retry-logik.

## Implementerings-todos

- [ ] **create-utils**: Opret utils.py med find_latest_file og estimér_køn funktioner
- [ ] **externalize-gender-data**: Flyt MANUEL_KØNSBESTEMMELSE til data/manuel_koen.json (kræver: create-utils)
- [ ] **refactor-json-to-excel**: Tilføj Parquet-export til valg_json_til_excel.py (kræver: create-utils)
- [ ] **update-analysis-scripts**: Opdater alle analyse-scripts til at bruge utils.py og læse Parquet (kræver: refactor-json-to-excel)
- [ ] **improve-sftp-robustness**: Tilføj retry-logik og fil-check til hent_valgdata.py
- [ ] **update-pipeline**: Opdater pipeline.py til at håndtere Parquet-filer (kræver: refactor-json-to-excel, update-analysis-scripts)

---

## 1. Opret utils.py med Genbrugelige Funktioner

**Mål:** Eliminér duplikeret kode ved at samle genbrugelige funktioner i central fil.

### Funktioner at flytte til utils.py:

```python
# utils.py
import pandas as pd
import json
from pathlib import Path
import glob
import gender_guesser.detector as gender

# Global gender detector
_gender_detector = gender.Detector()
_MANUEL_KØNSBESTEMMELSE = None

def load_gender_data():
    """Indlæs manuel kønsbestemmelse fra JSON"""
    global _MANUEL_KØNSBESTEMMELSE
    if _MANUEL_KØNSBESTEMMELSE is None:
        data_file = Path(__file__).parent / 'data' / 'manuel_koen.json'
        with open(data_file, 'r', encoding='utf-8') as f:
            _MANUEL_KØNSBESTEMMELSE = json.load(f)
    return _MANUEL_KØNSBESTEMMELSE

def estimér_køn(fornavn):
    """
    Estimerer køn baseret på fornavn.
    Returnerer tuple: (køn, metode)
    """
    # Kopiér logik fra valg_json_til_excel.py
    pass

def find_latest_file(pattern):
    """Find den nyeste fil der matcher pattern"""
    files = glob.glob(pattern)
    if not files:
        return None
    files.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)
    return files[0]

def save_parquet(df, filepath, description=""):
    """Gem DataFrame som Parquet med metadata"""
    df.to_parquet(filepath, engine='pyarrow', compression='snappy')
    print(f"✓ {description}: {Path(filepath).name} ({len(df)} rækker)")

def load_parquet(filepath):
    """Indlæs Parquet-fil"""
    return pd.read_parquet(filepath, engine='pyarrow')
```

### Filer der skal opdateres:
- `lav_kønsanalyse.py` - fjern lokal `find_latest_file()`, import fra utils
- `lav_generel_analyse.py` - fjern lokal `find_latest_file()`, import fra utils
- `lav_borgmester_analyse.py` - fjern lokal `find_latest_file()`, import fra utils
- `generate_findings.py` - fjern lokal `find_latest_file()`, import fra utils

---

## 2. Eksternalisér MANUEL_KØNSBESTEMMELSE til JSON

**Mål:** Fjern 597-linjes dictionary fra koden og gem den som struktureret data.

### Trin:

1. **Opret `data/` mappe:**
   ```bash
   mkdir -p data
   ```

2. **Konverter dictionary til JSON:**
   ```python
   # Script til at konvertere
   import json
   from valg_json_til_excel import MANUEL_KØNSBESTEMMELSE
   
   with open('data/manuel_koen.json', 'w', encoding='utf-8') as f:
       json.dump(MANUEL_KØNSBESTEMMELSE, f, ensure_ascii=False, indent=2)
   ```

3. **Opdater `utils.py`:**
   - Tilføj `load_gender_data()` funktion (se ovenfor)
   - Indlæs JSON ved første kald til `estimér_køn()`

4. **Opdater `valg_json_til_excel.py`:**
   - Fjern `MANUEL_KØNSBESTEMMELSE` dictionary
   - Import `estimér_køn` fra utils

5. **Tilføj til `.gitignore` (hvis relevant):**
   ```
   # Men i dette tilfælde skal data/manuel_koen.json være under version control
   ```

---

## 3. Migrer til Parquet for Interne Mellemregninger

**Mål:** Brug Parquet for interne mellemregninger (10-100x hurtigere), behold Excel som slutbruger-format.

### A. Opdater `valg_json_til_excel.py`

Tilføj Parquet-eksport i `process_json_files()` funktionen:

```python
def process_json_files(json_mappe, output_mappe):
    # ... eksisterende kode ...
    
    # Gem samlede data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    parquet_dir = output_mappe / 'parquet'
    parquet_dir.mkdir(exist_ok=True)

    # SAMLEDE FILER - GEM BÅDE PARQUET OG EXCEL
    if alle_kandidater:
        df = pd.DataFrame(alle_kandidater)
        
        # Parquet (primær, hurtig)
        parquet_fil = parquet_dir / f"kandidater_ALLE_VALG_{timestamp}.parquet"
        df.to_parquet(parquet_fil, engine='pyarrow', compression='snappy')
        print(f"✓ Parquet gemt: {parquet_fil.name}")
        
        # Excel (sekundær, kompatibilitet)
        excel_fil = output_mappe / f"kandidater_ALLE_VALG_{timestamp}.xlsx"
        df.to_excel(excel_fil, index=False, engine='openpyxl')
        print(f"✓ Excel gemt: {excel_fil.name}")
```

Gentag for:
- `kandidater_KOMMUNAL_`
- `kandidater_REGIONAL_`
- `valgresultater_ALLE_VALG_`
- `valgresultater_KOMMUNAL_`
- `valgresultater_REGIONAL_`
- `mandatfordeling_ALLE_VALG_`
- `mandatfordeling_KOMMUNAL_`
- `mandatfordeling_REGIONAL_`

### B. Opdater analyse-scripts til at læse Parquet

**I `lav_kønsanalyse.py`:**

```python
from utils import find_latest_file, load_parquet

def lav_kønsanalyse(output_dir='excel_output'):
    print("Finder nyeste datafiler...")
    parquet_dir = Path(output_dir) / 'parquet'
    
    # Læs Parquet i stedet for Excel
    kandidater_fil = find_latest_file(f'{parquet_dir}/kandidater_ALLE_VALG_*.parquet')
    if not kandidater_fil:
        # Fallback til Excel hvis Parquet ikke findes
        kandidater_fil = find_latest_file(f'{output_dir}/kandidater_ALLE_VALG_*.xlsx')
        df_kandidater = pd.read_excel(kandidater_fil)
    else:
        df_kandidater = load_parquet(kandidater_fil)
```

Samme mønster for:
- `lav_generel_analyse.py`
- `lav_borgmester_analyse.py`
- `generate_findings.py`

### C. Opdater `pipeline.py`

Tilføj parquet-mappe til organisation:

```python
def organize_files(self):
    folders = {
        '00_START_HER': 'Præsentationsfiler',
        '01_Kommunalvalg': 'Kommunalvalg data',
        # ... eksisterende mapper ...
        'parquet': 'Interne Parquet-filer (hurtig læsning)',
    }
```

### Fordele ved Parquet:
- **Hastighed:** 10-100x hurtigere indlæsning
- **Filstørrelse:** 50-80% mindre end Excel
- **Datatyper:** Bevarer præcist datatyper (ingen tab af foranstillede nuller)
- **Kompatibilitet:** Virker med Pandas, Polars, Dask, Spark

---

## 4. Tilføj Robusthed til SFTP Download

**Mål:** Undgå at starte forfra hvis download fejler ved fil 2500/2800.

### Opdater `hent_valgdata.py`

```python
import time

def download_file_with_retry(sftp, remote_path, local_path, max_retries=3):
    """Download fil med retry-logik og resume support"""
    
    # Tjek om filen allerede eksisterer
    if local_path.exists():
        try:
            remote_size = sftp.stat(remote_path).st_size
            local_size = local_path.stat().st_size
            
            if local_size == remote_size:
                print(f"  ✓ Allerede downloadet: {local_path.name}")
                return True
            else:
                print(f"  ⚠ Delvis download: {local_path.name} (lokal: {local_size}, remote: {remote_size})")
                local_path.unlink()  # Slet delvis fil
        except Exception:
            pass
    
    # Prøv at downloade med retries
    for attempt in range(1, max_retries + 1):
        try:
            sftp.get(remote_path, str(local_path))
            return True
        except Exception as e:
            if attempt < max_retries:
                wait_time = 2 ** attempt  # Exponential backoff: 2s, 4s, 8s
                print(f"  ⚠ Forsøg {attempt} fejlede: {e}")
                print(f"  ⏳ Venter {wait_time}s før retry...")
                time.sleep(wait_time)
            else:
                print(f"  ✗ Download fejlede efter {max_retries} forsøg: {e}")
                return False
    
    return False

def download_recursive(sftp, remote_path, local_path, indent=0):
    """Download filer rekursivt fra SFTP-server"""
    prefix = "  " * indent
    
    # ... eksisterende kode ...
    
    for item in items:
        remote_item = f"{remote_path}/{item.filename}".replace("//", "/")
        local_item = local_path / item.filename
        
        if stat_is_dir(item):
            # ... eksisterende mappe-håndtering ...
        else:
            if item.filename.endswith(".json"):
                print(f"{prefix}  ↓ {item.filename} ({format_size(item.st_size)})")
                
                # Brug ny retry-funktion
                success = download_file_with_retry(sftp, remote_item, local_item)
                
                if not success:
                    print(f"{prefix}    ⚠ Spring over (download fejlede)")
```

### Fordele:
- Springer over filer der allerede er downloadet
- Automatisk retry ved netværksfejl
- Exponential backoff for at undgå at overbelaste serveren
- Bedre logning af fejl

---

## 5. Validér og Test

### Testtrin:

1. **Test utils.py:**
   ```bash
   python -c "from utils import find_latest_file, estimér_køn; print(estimér_køn('Hans'))"
   ```

2. **Test JSON eksternalisering:**
   ```bash
   cat data/manuel_koen.json | head -20
   ```

3. **Test Parquet-generering:**
   ```bash
   python pipeline.py --convert
   ls -lh excel_output/parquet/
   ```

4. **Test analyse med Parquet:**
   ```bash
   python lav_kønsanalyse.py --output-dir excel_output
   ```

5. **Test fuld pipeline:**
   ```bash
   python pipeline.py --skip-download --all
   ```

6. **Verificér output:**
   - Tjek at `excel_output/00_START_HER/` indeholder de 3 analyse-Excel-filer
   - Tjek at `excel_output/parquet/` indeholder .parquet filer
   - Sammenlign hastighed: noter tid før/efter Parquet-migration

---

## Forventede Resultater

### Performance-forbedringer:
- **Konverteringstid:** Uændret (Parquet-skrivning er hurtig)
- **Analyse-indlæsning:** 10-100x hurtigere (Parquet vs Excel)
- **Filstørrelse:** 50-80% reduktion for Parquet-filer
- **Download-robusthed:** Færre fejl, resume-support

### Kodebase-forbedringer:
- **Mindre duplikering:** 4 scripts deler nu `find_latest_file()` og `estimér_køn()`
- **Bedre vedligeholdelighed:** Kønsdata kan opdateres uden at røre koden
- **Mere læsbar kode:** `valg_json_til_excel.py` går fra 754 til ~580 linjer

### Breaking changes:
- Ingen! Excel-filer genereres stadig som før
- Analyse-scripts har fallback til Excel hvis Parquet mangler

---

## Fremtidige Udvidelser (ikke i denne plan)

Disse kan implementeres senere, men ikke nu:

1. **Geografisk Visualisering** (folium/geopandas for interaktive kort)
2. **Mandattyveri-analyse** (partier med flest stemmer men ikke borgmesterpost)
3. **Parse borgmestre.md til CSV** (mere robust end regex-parsing)
4. **Pipeline som importérbare funktioner** (i stedet for subprocess calls)
5. **Async SFTP download** (parallel downloads for ekstra hastighed)

---

## Dependencies

Tilføj til `requirements.txt` hvis ikke allerede der:

```
pyarrow>=14.0.0      # Parquet support
fastparquet>=2023.0  # Alternativ Parquet engine (valgfri)
```

---

## Checkpoint

Efter implementering af denne plan:
- [ ] Alle tests kører succesfuldt
- [ ] Pipeline genererer både Parquet og Excel
- [ ] Analyse-scripts bruger Parquet som primær kilde
- [ ] SFTP download er mere robust
- [ ] Kønsdata er eksternaliseret til JSON
- [ ] Kodebase følger DRY-principper

