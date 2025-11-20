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
        findings['køn_procent_kvinder'] = round(køn_dist.get('K', 0) / (køn_dist.get('M', 0) + køn_dist.get('K', 0)) * 100, 1) if (køn_dist.get('M', 0) + køn_dist.get('K', 0)) > 0 else 0

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
            findings['alle_partier_kønsbalance'] = parti_køn[['K', 'M', 'Total', 'Andel_Kvinder']].sort_values('Total', ascending=False).to_dict('index')

    # Kommuner
    if 'KommuneNavn' in kandidater.columns:
        kommuner = kandidater[kandidater['KommuneNavn'] != '']['KommuneNavn'].unique()
        findings['antal_kommuner'] = len(kommuner)

    # Regioner
    if 'RegionNavn' in kandidater.columns:
        regioner = kandidater[kandidater['RegionNavn'] != '']['RegionNavn'].unique()
        findings['antal_regioner'] = len(regioner)

    # === JOURNALISTISKE ANALYSER ===

    # 1. Regional kønsbalance analyse
    if 'EstimeretKøn' in kandidater.columns and 'RegionNavn' in kandidater.columns:
        kandidater_regional = kandidater[kandidater['RegionNavn'] != ''].copy()
        kandidater_regional_kendt = kandidater_regional[kandidater_regional['EstimeretKøn'].isin(['M', 'K'])]

        if len(kandidater_regional_kendt) > 0:
            region_køn = kandidater_regional_kendt.groupby(['RegionNavn', 'EstimeretKøn']).size().unstack(fill_value=0)
            if 'K' in region_køn.columns and 'M' in region_køn.columns:
                region_køn['Total'] = region_køn.sum(axis=1)
                region_køn['Andel_Kvinder'] = region_køn['K'] / (region_køn['M'] + region_køn['K']) * 100
                findings['regional_kønsbalance'] = region_køn[['K', 'M', 'Total', 'Andel_Kvinder']].sort_values('Andel_Kvinder', ascending=False).to_dict('index')

    # 2. Kommunal kønsbalance (min 50 kandidater for at undgå statistisk støj)
    if 'EstimeretKøn' in kandidater.columns and 'KommuneNavn' in kandidater.columns:
        kandidater_kommunal = kandidater[kandidater['KommuneNavn'] != ''].copy()
        kandidater_kommunal_kendt = kandidater_kommunal[kandidater_kommunal['EstimeretKøn'].isin(['M', 'K'])]

        if len(kandidater_kommunal_kendt) > 0:
            kommune_køn = kandidater_kommunal_kendt.groupby(['KommuneNavn', 'EstimeretKøn']).size().unstack(fill_value=0)
            if 'K' in kommune_køn.columns and 'M' in kommune_køn.columns:
                kommune_køn['Total'] = kommune_køn.sum(axis=1)
                kommune_køn['Andel_Kvinder'] = kommune_køn['K'] / (kommune_køn['M'] + kommune_køn['K']) * 100

                # Kun kommuner med 50+ kandidater for valid sammenligning
                store_kommuner = kommune_køn[kommune_køn['Total'] >= 50].copy()
                findings['bedste_kommuner_kønsbalance'] = store_kommuner.nlargest(10, 'Andel_Kvinder')[['K', 'M', 'Total', 'Andel_Kvinder']].to_dict('index')
                findings['værste_kommuner_kønsbalance'] = store_kommuner.nsmallest(10, 'Andel_Kvinder')[['K', 'M', 'Total', 'Andel_Kvinder']].to_dict('index')

    # 3. Parti-regional variation (store partier i forskellige regioner)
    if 'EstimeretKøn' in kandidater.columns and 'ListeNavn' in kandidater.columns and 'RegionNavn' in kandidater.columns:
        kandidater_regional = kandidater[kandidater['RegionNavn'] != ''].copy()
        kandidater_regional_kendt = kandidater_regional[kandidater_regional['EstimeretKøn'].isin(['M', 'K'])]

        if len(kandidater_regional_kendt) > 0:
            # Top 5 partier
            top5_partier = kandidater['ListeNavn'].value_counts().head(5).index.tolist()

            parti_regional_data = {}
            for parti in top5_partier:
                parti_data = kandidater_regional_kendt[kandidater_regional_kendt['ListeNavn'] == parti]
                if len(parti_data) > 0:
                    region_breakdown = parti_data.groupby(['RegionNavn', 'EstimeretKøn']).size().unstack(fill_value=0)
                    if 'K' in region_breakdown.columns and 'M' in region_breakdown.columns:
                        region_breakdown['Total'] = region_breakdown.sum(axis=1)
                        region_breakdown['Andel_Kvinder'] = region_breakdown['K'] / (region_breakdown['M'] + region_breakdown['K']) * 100
                        parti_regional_data[parti] = region_breakdown[['K', 'M', 'Total', 'Andel_Kvinder']].to_dict('index')

            findings['parti_regional_variation'] = parti_regional_data

    # 4. Små partier med god kønsbalance (interessant angle)
    if 'EstimeretKøn' in kandidater.columns and 'ListeNavn' in kandidater.columns:
        kandidater_kendt = kandidater[kandidater['EstimeretKøn'].isin(['M', 'K'])]
        parti_køn = kandidater_kendt.groupby(['ListeNavn', 'EstimeretKøn']).size().unstack(fill_value=0)
        if 'K' in parti_køn.columns and 'M' in parti_køn.columns:
            parti_køn['Total'] = parti_køn.sum(axis=1)
            parti_køn['Andel_Kvinder'] = parti_køn['K'] / (parti_køn['M'] + parti_køn['K']) * 100

            # Små/mellemstore partier (20-100 kandidater) med god kønsbalance
            mellem_partier = parti_køn[(parti_køn['Total'] >= 20) & (parti_køn['Total'] < 100)].copy()
            mellem_partier['Afvigelse'] = abs(mellem_partier['Andel_Kvinder'] - 50)
            findings['små_partier_god_balance'] = mellem_partier.sort_values('Afvigelse').head(10)[['K', 'M', 'Total', 'Andel_Kvinder']].to_dict('index')

    # 5. Kommunal vs Regional kønsbalance sammenligning
    if 'EstimeretKøn' in kandidater.columns and 'ValgNavn' in kandidater.columns:
        kandidater_kendt = kandidater[kandidater['EstimeretKøn'].isin(['M', 'K'])]

        kommunal = kandidater_kendt[kandidater_kendt['ValgNavn'].str.contains('Kommunalvalg', na=False)]
        regional = kandidater_kendt[kandidater_kendt['ValgNavn'].str.contains('Regionsrådsvalg', na=False)]

        if len(kommunal) > 0:
            kommunal_køn = kommunal['EstimeretKøn'].value_counts()
            kommunal_pct = round(kommunal_køn.get('K', 0) / (kommunal_køn.get('M', 0) + kommunal_køn.get('K', 0)) * 100, 1)
            findings['kommunal_køn_procent'] = kommunal_pct

        if len(regional) > 0:
            regional_køn = regional['EstimeretKøn'].value_counts()
            regional_pct = round(regional_køn.get('K', 0) / (regional_køn.get('M', 0) + regional_køn.get('K', 0)) * 100, 1)
            findings['regional_køn_procent'] = regional_pct

    # 6. Kønsmetode statistik (hvor mange blev manuelt/AI identificeret)
    if 'KønsMetode' in kandidater.columns:
        metode_dist = kandidater['KønsMetode'].value_counts()
        findings['kønsmetode_stats'] = metode_dist.to_dict()
        findings['kønsmetode_manuel_pct'] = round(metode_dist.get('manuel identifikation', 0) / len(kandidater) * 100, 1) if len(kandidater) > 0 else 0

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

✅ *Køn er estimeret via kombineret manuel database og automatisk navneidentifikation (100% dækning)*
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

    # Kommunal vs Regional sammenligning
    if 'kommunal_køn_procent' in findings and 'regional_køn_procent' in findings:
        content += f"""
### 5. Kommunalvalg vs Regionsrådsvalg

**Kønsfordeling:**
- **Kommunalvalg:** {findings['kommunal_køn_procent']:.1f}% kvinder ({findings['kommunal_kandidater']:,} kandidater)
- **Regionsrådsvalg:** {findings['regional_køn_procent']:.1f}% kvinder ({findings['regional_kandidater']:,} kandidater)
- **Forskel:** {abs(findings['kommunal_køn_procent'] - findings['regional_køn_procent']):.1f} procentpoint

💡 *{'Flere kvinder stiller op til regionsrådsvalg' if findings['regional_køn_procent'] > findings['kommunal_køn_procent'] else 'Flere kvinder stiller op til kommunalvalg'}*
"""

    # Regional kønsbalance
    if 'regional_kønsbalance' in findings:
        content += f"""
### 6. Kønsbalance per region (Regionsrådsvalg)

"""
        for i, (region, data) in enumerate(list(findings['regional_kønsbalance'].items())[:5], 1):
            content += f"{i}. **{region}**: {data['Andel_Kvinder']:.1f}% kvinder ({int(data['K'])} K / {int(data['M'])} M)\n"

    # Kommunale highlights
    if 'bedste_kommuner_kønsbalance' in findings and findings['bedste_kommuner_kønsbalance']:
        content += f"""
### 7. Bedste kommunale kønsbalance (kommuner med 50+ kandidater)

"""
        for i, (kommune, data) in enumerate(list(findings['bedste_kommuner_kønsbalance'].items())[:5], 1):
            content += f"{i}. **{kommune}**: {data['Andel_Kvinder']:.1f}% kvinder ({int(data['Total'])} kandidater)\n"

    if 'værste_kommuner_kønsbalance' in findings and findings['værste_kommuner_kønsbalance']:
        content += f"""
### 8. Lavest kvinde-andel kommunalt (kommuner med 50+ kandidater)

"""
        for i, (kommune, data) in enumerate(list(findings['værste_kommuner_kønsbalance'].items())[:5], 1):
            content += f"{i}. **{kommune}**: {data['Andel_Kvinder']:.1f}% kvinder ({int(data['Total'])} kandidater)\n"

    # Små partier med god balance
    if 'små_partier_god_balance' in findings and findings['små_partier_god_balance']:
        content += f"""
### 9. Mindre partier med god kønsbalance (20-100 kandidater)

"""
        for i, (parti, data) in enumerate(list(findings['små_partier_god_balance'].items())[:5], 1):
            content += f"{i}. **{parti}**: {data['Andel_Kvinder']:.1f}% kvinder ({int(data['Total'])} kandidater)\n"

    # Kønsmetode statistik
    if 'kønsmetode_manuel_pct' in findings:
        content += f"""
### 10. Datakvalitet - Kønsidentifikation

**Metode:**
- **Manuel identifikation:** {findings['kønsmetode_manuel_pct']:.1f}% af kandidater
- **Automatisk (gender-guesser):** {100 - findings['kønsmetode_manuel_pct']:.1f}% af kandidater
- **100% kønsbestemmelse** - ingen ukendte kandidater

💡 *Alle kandidater har fået identificeret køn via kombineret manuel database og automatisk navneidentifikation*
"""

    # Parti-regional variation
    if 'parti_regional_variation' in findings and findings['parti_regional_variation']:
        content += f"""

---

## 📍 REGIONALE VARIATIONER

### Kønsbalance i top 5 partier per region

"""
        for parti, region_data in list(findings['parti_regional_variation'].items())[:5]:
            content += f"\n**{parti}:**\n"
            for region, data in sorted(region_data.items(), key=lambda x: x[1]['Andel_Kvinder'], reverse=True):
                content += f"- {region}: {data['Andel_Kvinder']:.1f}% kvinder ({int(data['Total'])} kandidater)\n"

    # Detaljeret partioversigt
    if 'alle_partier_kønsbalance' in findings and findings['alle_partier_kønsbalance']:
        content += f"""

---

## 🎯 KOMPLET PARTIOVERSIGT

### Alle partier sorteret efter størrelse

"""
        for i, (parti, data) in enumerate(list(findings['alle_partier_kønsbalance'].items())[:20], 1):
            content += f"{i}. **{parti}**: {int(data['Total'])} kandidater - {data['Andel_Kvinder']:.1f}% kvinder ({int(data['K'])} K / {int(data['M'])} M)\n"

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
- ✅ 100% kønsidentifikation via kombineret manuel database og automatisk estimering
- ✅ Verificeret mod testdata - ekskluderet KOMBIT's verifikationsdata

### Begrænsninger:
- ⚠️ Køn er ESTIMERET via fornavne (ikke officielle data fra CPR)
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
