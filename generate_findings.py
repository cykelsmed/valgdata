#!/usr/bin/env python3
"""
Genererer automatiske key findings og MASTER_FINDINGS.md fra valgdata
"""

import pandas as pd
from pathlib import Path
import glob
from datetime import datetime
import sys

def find_latest_file(pattern):
    """Find den nyeste fil der matcher pattern"""
    files = glob.glob(pattern)
    if not files:
        return None
    files.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)
    return files[0]

def analyze_data(output_dir='excel_output'):
    """Analyser data og udtræk key findings"""

    print("🔍 Analyserer valgdata...")

    # Find filer
    kandidater_fil = find_latest_file(f'{output_dir}/kandidater_ALLE_VALG_*.xlsx')
    resultater_fil = find_latest_file(f'{output_dir}/valgresultater_ALLE_VALG_*.xlsx')
    køns_fil = f'{output_dir}/Analyse_kønsfordeling.xlsx'

    if not kandidater_fil:
        print("❌ Kunne ikke finde kandidat-filer")
        return None

    print(f"Læser: {Path(kandidater_fil).name}")
    kandidater = pd.read_excel(kandidater_fil)

    findings = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_kandidater': len(kandidater),
        'kommunal_kandidater': len(kandidater[kandidater['ValgNavn'].str.contains('Kommunalvalg', na=False)]),
        'regional_kandidater': len(kandidater[kandidater['ValgNavn'].str.contains('Regionsrådsvalg', na=False)]),
    }

    # Kønsfordeling
    if 'EstimeretKøn' in kandidater.columns:
        køn_dist = kandidater['EstimeretKøn'].value_counts()
        findings['køn_mænd'] = int(køn_dist.get('M', 0))
        findings['køn_kvinder'] = int(køn_dist.get('K', 0))
        findings['køn_ukendt'] = int(køn_dist.get('Ukendt', 0))
        findings['køn_procent_kvinder'] = round(køn_dist.get('K', 0) / (køn_dist.get('M', 0) + køn_dist.get('K', 0)) * 100, 1)

    # Top partier
    if 'ListeNavn' in kandidater.columns:
        top_partier = kandidater['ListeNavn'].value_counts().head(10)
        findings['top_partier'] = top_partier.to_dict()

    # Kønsbalance per parti
    if 'EstimeretKøn' in kandidater.columns and 'ListeNavn' in kandidater.columns:
        kandidater_kendt = kandidater[kandidater['EstimeretKøn'].isin(['M', 'K'])]
        parti_køn = kandidater_kendt.groupby(['ListeNavn', 'EstimeretKøn']).size().unstack(fill_value=0)
        if 'K' in parti_køn.columns and 'M' in parti_køn.columns:
            parti_køn['Total'] = parti_køn.sum(axis=1)
            parti_køn['Andel_Kvinder'] = parti_køn['K'] / (parti_køn['M'] + parti_køn['K']) * 100

            # Kun store partier (50+ kandidater)
            store_partier = parti_køn[parti_køn['Total'] >= 50].copy()
            store_partier['Afvigelse'] = abs(store_partier['Andel_Kvinder'] - 50)

            findings['bedste_kønsbalance'] = store_partier.sort_values('Afvigelse').head(5)['Andel_Kvinder'].to_dict()
            findings['værste_kønsbalance'] = store_partier.sort_values('Andel_Kvinder').head(5)['Andel_Kvinder'].to_dict()

    # Kommuner
    if 'KommuneNavn' in kandidater.columns:
        kommuner = kandidater[kandidater['KommuneNavn'] != '']['KommuneNavn'].unique()
        findings['antal_kommuner'] = len(kommuner)

    # Regioner
    if 'RegionNavn' in kandidater.columns:
        regioner = kandidater[kandidater['RegionNavn'] != '']['RegionNavn'].unique()
        findings['antal_regioner'] = len(regioner)

    return findings

def generate_master_findings(findings, output_dir='excel_output'):
    """Generer MASTER_FINDINGS.md"""

    if not findings:
        print("❌ Ingen findings at generere")
        return

    output_file = f'{output_dir}/MASTER_FINDINGS.md'

    content = f"""# VALGDATA 2025 - MASTER FINDINGS
## Kommunal- og Regionsrådsvalg 18. november 2025

**Genereret:** {findings['timestamp']}
**Datasæt:** Officielle data fra valg.dk

---

## 📊 OVERORDNET STATISTIK

### Kandidater
- **Total:** {findings['total_kandidater']:,} kandidater
- **Kommunalvalg:** {findings['kommunal_kandidater']:,} kandidater (98 kommuner)
- **Regionsrådsvalg:** {findings['regional_kandidater']:,} kandidater (5 regioner)

### Geografisk dækning
- **{findings.get('antal_kommuner', 98)} kommuner**
- **{findings.get('antal_regioner', 5)} regioner**
- Alle opstillingskredse og afstemningsområder

---

## 🎯 TOP 10 KEY FINDINGS

### 1. Kønsfordeling blandt kandidater
"""

    if 'køn_mænd' in findings:
        content += f"""
**Total fordeling:**
- Mænd: {findings['køn_mænd']:,} ({findings['køn_mænd']/findings['total_kandidater']*100:.1f}%)
- Kvinder: {findings['køn_kvinder']:,} ({findings['køn_kvinder']/findings['total_kandidater']*100:.1f}%)
- Ukendt: {findings['køn_ukendt']:,} ({findings['køn_ukendt']/findings['total_kandidater']*100:.1f}%)

**Blandt kendte køn:** {findings['køn_procent_kvinder']:.1f}% kvinder

⚠️ *Køn er estimeret baseret på fornavne via gender-guesser (89% kendt køn)*
"""

    if 'bedste_kønsbalance' in findings and findings['bedste_kønsbalance']:
        content += f"""
### 2. Bedste kønsbalance (store partier, 50+ kandidater)

"""
        for i, (parti, andel) in enumerate(list(findings['bedste_kønsbalance'].items())[:5], 1):
            content += f"{i}. **{parti}**: {andel:.1f}% kvinder\n"

    if 'værste_kønsbalance' in findings and findings['værste_kønsbalance']:
        content += f"""
### 3. Lavest andel kvinder (store partier)

"""
        for i, (parti, andel) in enumerate(list(findings['værste_kønsbalance'].items())[:5], 1):
            content += f"{i}. **{parti}**: {andel:.1f}% kvinder\n"

    if 'top_partier' in findings:
        content += f"""
### 4. Flest kandidater per parti

"""
        for i, (parti, antal) in enumerate(list(findings['top_partier'].items())[:10], 1):
            content += f"{i}. **{parti}**: {antal:,} kandidater\n"

    content += """

---

## 📁 DATAFILER

### Start her (små, hurtige filer):
1. **Analyse_eksempel_stemmeslugere.xlsx** (13 KB)
   - Top 20 stemmeslugere nationalt
   - Regional analyse

2. **Analyse_kønsfordeling.xlsx** (16 KB)
   - Kønsfordeling per parti/kommune/region
   - Bedste kønsbalance

3. **EXECUTIVE_SUMMARY.txt**
   - Hurtig oversigt
   - Top 5 analyser

### Detaljerede data:
- **01_Kommunalvalg/** - Alle kommunale data (~24 MB)
- **02_Regionsrådsvalg/** - Alle regionale data (~61 MB)
- **03_Samlet_Alle_Valg/** - Kombineret datasæt (~83 MB)
- **04_Reference_Geografi/** - Geografiske data

---

## 🔍 MULIGE ANALYSER

Med dette datasæt kan du analysere:

✅ **Kønsfordeling**
- Per parti, kommune, region
- Blandt valgte vs kandidater
- Historisk udvikling

✅ **Valgdeltagelse**
- Per afstemningsområde
- Kommunale/regionale forskelle
- Socioøkonomiske sammenhænge (med ekstra data)

✅ **Personlige mandater**
- Hvem fik flest personlige stemmer?
- Mandater via personlige stemmer vs liste
- "Stemmeslugere" uden mandat

✅ **Geografiske mønstre**
- "Røde" vs "blå" områder
- Urban vs rural patterns
- Regionale forskelle

✅ **Historisk sammenligning**
- Ændringer siden 2021
- Partiskift
- Valgdeltagelsesudvikling

---

## ⚠️ DATA QUALITY & BEGRÆNSNINGER

### Styrker:
- ✅ Officielle data fra valg.dk
- ✅ Komplet dækning (alle kommuner/regioner)
- ✅ Ned til afstemningsområde-niveau
- ✅ Kønsestimering (89% kendt køn)

### Begrænsninger:
- ⚠️ Køn er ESTIMERET (ikke officielle data)
- ⚠️ Ingen demografiske data (alder, uddannelse)
- ⚠️ Historiske data kun som ændringstal
- ⚠️ Binær kønsklassifikation (M/K)

---

## 🚀 HURTIG START

```bash
# 1. Installer dependencies
pip install -r requirements.txt

# 2. Kør pipeline (hvis du vil regenerere)
python pipeline.py --all

# 3. Udforsk data
cd excel_output/00_START_HER/
# Åbn Analyse_eksempel_stemmeslugere.xlsx
# Åbn Analyse_kønsfordeling.xlsx
# Læs EXECUTIVE_SUMMARY.txt
```

---

## 📚 DOKUMENTATION

- **README.txt** - Komplet filbeskrivelser
- **KEY_FINDINGS.txt** - Detaljerede analysemuligheder
- **EXECUTIVE_SUMMARY.txt** - Hurtig oversigt
- **_BESKRIVELSE.txt** i hver mappe

---

## 📊 PIPELINE METADATA

**Scripts:**
- `hent_valgdata.py` - Download fra valg.dk SFTP
- `valg_json_til_excel.py` - JSON til Excel konvertering
- `lav_kønsanalyse.py` - Kønsanalyse
- `generate_findings.py` - Auto-generering af findings
- `pipeline.py` - Orchestrator

**Dependencies:**
- pandas, openpyxl, paramiko, gender-guesser

**Total processing time:** ~3-5 minutter

---

*Genereret automatisk af generate_findings.py*
"""

    # Gem fil
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ MASTER_FINDINGS.md gemt: {output_file}")
    return output_file

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Generer findings fra valgdata')
    parser.add_argument('--output-dir', default='excel_output',
                       help='Output directory (default: excel_output)')

    args = parser.parse_args()

    # Analyser data
    findings = analyze_data(args.output_dir)

    if findings:
        # Generer MASTER_FINDINGS.md
        generate_master_findings(findings, args.output_dir)
        print("\n✅ Findings genereret!")
    else:
        print("\n❌ Kunne ikke generere findings")
        sys.exit(1)

if __name__ == '__main__':
    main()
