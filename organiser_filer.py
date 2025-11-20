#!/usr/bin/env python3
"""
Organiserer Excel-filer i overskuelig mappestruktur
"""

import shutil
from pathlib import Path

def organiser_filer():
    """Organiser alle Excel-filer i strukturerede mapper"""

    output_dir = Path('excel_output')

    # Definer mapper
    kommunal_kandidater = output_dir / '01_Kommunalvalg' / 'kandidater'
    kommunal_resultater = output_dir / '01_Kommunalvalg' / 'valgresultater'
    kommunal_deltagelse = output_dir / '01_Kommunalvalg' / 'valgdeltagelse'
    kommunal_mandater = output_dir / '01_Kommunalvalg' / 'mandatfordeling'

    regional_kandidater = output_dir / '02_Regionsrådsvalg' / 'kandidater'
    regional_resultater = output_dir / '02_Regionsrådsvalg' / 'valgresultater'
    regional_deltagelse = output_dir / '02_Regionsrådsvalg' / 'valgdeltagelse'
    regional_mandater = output_dir / '02_Regionsrådsvalg' / 'mandatfordeling'

    samlet_dir = output_dir / '03_Samlet_Alle_Valg'
    geografi_dir = output_dir / '04_Reference_Geografi'

    print("📁 Organiserer filer...")

    # Find og flyt kandidat-filer
    print("\n1. Flytter kandidat-filer...")
    for fil in output_dir.glob('kandidat-data-Kommunalvalg-*.xlsx'):
        shutil.move(str(fil), str(kommunal_kandidater / fil.name))
        print(f"  → {fil.name}")

    for fil in output_dir.glob('kandidat-data-Regionsrådsvalg-*.xlsx'):
        shutil.move(str(fil), str(regional_kandidater / fil.name))
        print(f"  → {fil.name}")

    # Flyt de seneste *_KOMMUNAL_* og *_REGIONAL_* kandidater
    kommunal_kand_filer = sorted(output_dir.glob('kandidater_KOMMUNAL_*.xlsx'), key=lambda x: x.stat().st_mtime)
    if kommunal_kand_filer:
        seneste = kommunal_kand_filer[-1]
        shutil.move(str(seneste), str(kommunal_kandidater / seneste.name))
        print(f"  → {seneste.name}")

    regional_kand_filer = sorted(output_dir.glob('kandidater_REGIONAL_*.xlsx'), key=lambda x: x.stat().st_mtime)
    if regional_kand_filer:
        seneste = regional_kand_filer[-1]
        shutil.move(str(seneste), str(regional_kandidater / seneste.name))
        print(f"  → {seneste.name}")

    # Find og flyt valgresultat-filer
    print("\n2. Flytter valgresultat-filer...")
    for fil in output_dir.glob('valgresultater-Kommunalvalg-*.xlsx'):
        shutil.move(str(fil), str(kommunal_resultater / fil.name))
        print(f"  → {fil.name}")

    for fil in output_dir.glob('valgresultater-Regionsrådsvalg-*.xlsx'):
        shutil.move(str(fil), str(regional_resultater / fil.name))
        print(f"  → {fil.name}")

    # Flyt seneste *_ALLE_VALG_* valgresultater
    alle_result_filer = sorted(output_dir.glob('valgresultater_ALLE_VALG_*.xlsx'), key=lambda x: x.stat().st_mtime)
    if alle_result_filer:
        seneste = alle_result_filer[-1]
        shutil.move(str(seneste), str(samlet_dir / seneste.name))
        print(f"  → {seneste.name}")

    # Find og flyt valgdeltagelse-filer
    print("\n3. Flytter valgdeltagelse-filer...")
    count = 0
    for fil in output_dir.glob('valgdeltagelse-Kommunalvalg-*.xlsx'):
        shutil.move(str(fil), str(kommunal_deltagelse / fil.name))
        count += 1
        if count % 100 == 0:
            print(f"  → Flyttet {count} kommunale valgdeltagelse-filer...")
    print(f"  ✓ {count} kommunale valgdeltagelse-filer flyttet")

    count = 0
    for fil in output_dir.glob('valgdeltagelse-Regionsrådsvalg-*.xlsx'):
        shutil.move(str(fil), str(regional_deltagelse / fil.name))
        count += 1
        if count % 100 == 0:
            print(f"  → Flyttet {count} regionale valgdeltagelse-filer...")
    print(f"  ✓ {count} regionale valgdeltagelse-filer flyttet")

    # Find og flyt mandatfordeling-filer
    print("\n4. Flytter mandatfordeling-filer...")
    for fil in output_dir.glob('mandatfordeling-Kommunalvalg-*.xlsx'):
        shutil.move(str(fil), str(kommunal_mandater / fil.name))
        print(f"  → {fil.name}")

    for fil in output_dir.glob('mandatfordeling-Regionsrådsvalg-*.xlsx'):
        shutil.move(str(fil), str(regional_mandater / fil.name))
        print(f"  → {fil.name}")

    # Flyt seneste mandatfordeling filer
    kommunal_mandat_filer = sorted(output_dir.glob('mandatfordeling_KOMMUNAL_*.xlsx'), key=lambda x: x.stat().st_mtime)
    if kommunal_mandat_filer:
        seneste = kommunal_mandat_filer[-1]
        shutil.move(str(seneste), str(kommunal_mandater / seneste.name))
        print(f"  → {seneste.name}")

    regional_mandat_filer = sorted(output_dir.glob('mandatfordeling_REGIONAL_*.xlsx'), key=lambda x: x.stat().st_mtime)
    if regional_mandat_filer:
        seneste = regional_mandat_filer[-1]
        shutil.move(str(seneste), str(regional_mandater / seneste.name))
        print(f"  → {seneste.name}")

    alle_mandat_filer = sorted(output_dir.glob('mandatfordeling_ALLE_VALG_*.xlsx'), key=lambda x: x.stat().st_mtime)
    if alle_mandat_filer:
        seneste = alle_mandat_filer[-1]
        shutil.move(str(seneste), str(samlet_dir / seneste.name))
        print(f"  → {seneste.name}")

    # Flyt geografi-filer
    print("\n5. Flytter geografi-filer...")
    for fil in output_dir.glob('*-111120250750.xlsx'):
        shutil.move(str(fil), str(geografi_dir / fil.name))
        print(f"  → {fil.name}")

    # Flyt seneste kombinerede kandidater til samlet mappe
    print("\n6. Flytter samlede filer...")
    alle_kand_filer = sorted(output_dir.glob('kandidater_ALLE_VALG_*.xlsx'), key=lambda x: x.stat().st_mtime)
    if alle_kand_filer:
        seneste = alle_kand_filer[-1]
        shutil.move(str(seneste), str(samlet_dir / seneste.name))
        print(f"  → {seneste.name}")

    # Flyt pivot-tabel
    pivot_filer = sorted(output_dir.glob('resultater_per_kommune_region_*.xlsx'), key=lambda x: x.stat().st_mtime)
    if pivot_filer:
        seneste = pivot_filer[-1]
        shutil.move(str(seneste), str(samlet_dir / seneste.name))
        print(f"  → {seneste.name}")

    print("\n✅ Alle filer organiseret!")

    # Vis oversigt
    print("\n📊 Mappestruktur:")
    print(f"  01_Kommunalvalg/kandidater: {len(list(kommunal_kandidater.glob('*.xlsx')))} filer")
    print(f"  01_Kommunalvalg/valgresultater: {len(list(kommunal_resultater.glob('*.xlsx')))} filer")
    print(f"  01_Kommunalvalg/valgdeltagelse: {len(list(kommunal_deltagelse.glob('*.xlsx')))} filer")
    print(f"  01_Kommunalvalg/mandatfordeling: {len(list(kommunal_mandater.glob('*.xlsx')))} filer")
    print(f"  02_Regionsrådsvalg/kandidater: {len(list(regional_kandidater.glob('*.xlsx')))} filer")
    print(f"  02_Regionsrådsvalg/valgresultater: {len(list(regional_resultater.glob('*.xlsx')))} filer")
    print(f"  02_Regionsrådsvalg/valgdeltagelse: {len(list(regional_deltagelse.glob('*.xlsx')))} filer")
    print(f"  02_Regionsrådsvalg/mandatfordeling: {len(list(regional_mandater.glob('*.xlsx')))} filer")
    print(f"  03_Samlet_Alle_Valg: {len(list(samlet_dir.glob('*.xlsx')))} filer")
    print(f"  04_Reference_Geografi: {len(list(geografi_dir.glob('*.xlsx')))} filer")

if __name__ == '__main__':
    organiser_filer()
