#!/usr/bin/env python3
"""
Valgdata Pipeline - Automatiseret data processing
Kommunal- og Regionsrådsvalg 2025

Usage:
    python pipeline.py --all               # Kør hele pipeline
    python pipeline.py --download          # Kun download
    python pipeline.py --convert           # Kun konvertering
    python pipeline.py --analyze           # Kun analyse
    python pipeline.py --clean --all       # Slet gamle filer og kør alt
"""

import sys
import shutil
from pathlib import Path
import argparse
from datetime import datetime

# Import alle pipeline-moduler
from hent_valgdata import main as hent_data_main
from valg_json_til_excel import main as convert_main
from lav_kønsanalyse import main as kønsanalyse_main
from lav_generel_analyse import main as generel_analyse_main
from lav_borgmester_analyse import main as borgmester_analyse_main
from parse_borgmestre import main as parse_borgmestre_main
from generate_findings import main as generate_findings_main
from validate_data import main as validate_data_main

class Pipeline:
    def __init__(self, json_dir='json_data', output_dir='excel_output'):
        self.json_dir = Path(json_dir)
        self.output_dir = Path(output_dir)
        self.log_file = 'pipeline.log'
        self.start_time = datetime.now()

    def log(self, message, level='INFO'):
        """Log besked til konsol og fil"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] [{level}] {message}"
        print(log_msg)

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')

    def run_function(self, func, description, *args, **kwargs):
        """Kør en funktion og log resultatet"""
        self.log(f"{'='*60}")
        self.log(f"Starter: {description}")

        try:
            result = func(*args, **kwargs)
            self.log(f"✅ Succes: {description}", 'SUCCESS')
            return True

        except Exception as e:
            self.log(f"❌ Fejl: {description}", 'ERROR')
            self.log(f"Exception: {type(e).__name__}: {str(e)}", 'ERROR')
            import traceback
            self.log(f"Traceback:\n{traceback.format_exc()}", 'ERROR')
            return False

    def clean(self):
        """Slet gamle genererede filer"""
        self.log("🗑️  Sletter gamle filer...")

        # Slet output directory
        if self.output_dir.exists():
            self.log(f"Sletter: {self.output_dir}")
            shutil.rmtree(self.output_dir)

        # Valgfrit: Slet JSON data (kommenteret ud - spar tid)
        # if self.json_dir.exists():
        #     self.log(f"Sletter: {self.json_dir}")
        #     shutil.rmtree(self.json_dir)

        # Genopret output directory
        self.output_dir.mkdir(exist_ok=True)

        self.log("✅ Oprydning færdig")

    def download(self):
        """Download JSON data fra valg.dk"""
        self.log("📥 Downloader valgdata...")

        self.json_dir.mkdir(exist_ok=True)

        return self.run_function(hent_data_main, "Download valgdata fra valg.dk", str(self.json_dir))

    def convert(self):
        """Konverter JSON til Excel"""
        self.log("🔄 Konverterer JSON til Excel...")

        if not self.json_dir.exists():
            self.log("❌ JSON directory findes ikke. Kør --download først.", 'ERROR')
            return False

        self.output_dir.mkdir(exist_ok=True)

        return self.run_function(convert_main, "Konvertering til Excel med kønsestimering", 
                                str(self.json_dir), str(self.output_dir))

    def analyze_gender(self):
        """Lav kønsanalyse"""
        self.log("👥 Laver kønsanalyse...")

        return self.run_function(kønsanalyse_main, "Kønsanalyse", str(self.output_dir))

    def analyze_general(self):
        """Lav generel analyse (valgdeltagelse, job, stemmeslugere)"""
        self.log("📊 Laver generel analyse (valgdeltagelse, job, stemmeslugere)...")

        return self.run_function(generel_analyse_main, "Generel Analyse", str(self.output_dir))

    def analyze_borgmestre(self):
        """Parse og analyser borgmester-data"""
        self.log("👔 Laver borgmester-analyse...")

        # Parse borgmestre.md først
        if not Path('borgmestre_parsed.csv').exists():
            if not self.run_function(parse_borgmestre_main, "Parsing borgmestre.md"):
                return False

        # Lav analyse
        return self.run_function(borgmester_analyse_main, "Borgmester Analyse", str(self.output_dir))

    def generate_findings(self):
        """Generer findings og MASTER_FINDINGS.md"""
        self.log("📊 Genererer findings...")

        return self.run_function(generate_findings_main, "Findings generation", str(self.output_dir))

    def validate_data(self):
        """Valider data for fejl og realistiske værdier"""
        self.log("✅ Validerer data...")

        return self.run_function(validate_data_main, "Data validering", str(self.output_dir))

    def organize_files(self):
        """Organiser filer i mapper"""
        self.log("📁 Organiserer filer...")

        # Opret undermapper
        folders = {
            '00_START_HER': 'Præsentationsfiler',
            '01_Kommunalvalg': 'Kommunalvalg data',
            '02_Regionsrådsvalg': 'Regionsrådsvalg data',
            '03_Samlet_Alle_Valg': 'Samlet data',
            '04_Reference_Geografi': 'Geografiske data',
            '05_Valgdeltagelse_Kommunal': 'Valgdeltagelse per opstillingskreds - Kommunalvalg',
            '06_Valgdeltagelse_Regional': 'Valgdeltagelse per opstillingskreds - Regionsrådsvalg',
            'parquet': 'Interne Parquet-filer (hurtig læsning)'
        }

        for folder_name, description in folders.items():
            folder_path = self.output_dir / folder_name
            folder_path.mkdir(exist_ok=True)
            self.log(f"  ✓ {folder_name}/ - {description}")

        # Flyt analyse-filer til START_HER (hvis de ikke allerede er der)
        # Note: MASTER_FINDINGS.md skrives nu direkte til 00_START_HER af generate_findings.py
        for file in ['Analyse_kønsfordeling.xlsx', 'Analyse_generel.xlsx', 'Analyse_borgmestre.xlsx']:
            src = self.output_dir / file
            if src.exists():
                dst = self.output_dir / '00_START_HER' / file
                shutil.copy2(src, dst)
                self.log(f"  → {file} → 00_START_HER/")

        # Organiser alle Excel-filer i root
        self.log("\n📦 Organiserer Excel-filer...")
        file_count = {'kommunal': 0, 'regional': 0, 'samlet': 0, 'geografi': 0, 'valgdelt_k': 0, 'valgdelt_r': 0}

        for excel_file in self.output_dir.glob('*.xlsx'):
            filename = excel_file.name

            # Skip analyse-filer (allerede håndteret)
            if filename.startswith('Analyse_'):
                continue

            # Valgdeltagelse-filer (2500+ filer)
            if filename.startswith('valgdeltagelse-Kommunalvalg-'):
                dst = self.output_dir / '05_Valgdeltagelse_Kommunal' / filename
                shutil.move(str(excel_file), str(dst))
                file_count['valgdelt_k'] += 1
            elif filename.startswith('valgdeltagelse-Regionsrådsvalg-'):
                dst = self.output_dir / '06_Valgdeltagelse_Regional' / filename
                shutil.move(str(excel_file), str(dst))
                file_count['valgdelt_r'] += 1

            # Kommunalvalg data
            elif '_KOMMUNAL_' in filename:
                dst = self.output_dir / '01_Kommunalvalg' / filename
                shutil.move(str(excel_file), str(dst))
                file_count['kommunal'] += 1

            # Regionsrådsvalg data
            elif '_REGIONAL_' in filename:
                dst = self.output_dir / '02_Regionsrådsvalg' / filename
                shutil.move(str(excel_file), str(dst))
                file_count['regional'] += 1

            # Samlet data (ALLE_VALG eller resultater_per_kommune_region)
            elif '_ALLE_VALG_' in filename or filename.startswith('resultater_per_'):
                dst = self.output_dir / '03_Samlet_Alle_Valg' / filename
                shutil.move(str(excel_file), str(dst))
                file_count['samlet'] += 1

            # Geografiske reference-filer
            elif any(x in filename for x in ['Kommune-', 'Region-', 'Afstemningsomraade-',
                                              'Opstillingskreds-', 'Storkreds-', 'Valglandsdel-']):
                dst = self.output_dir / '04_Reference_Geografi' / filename
                shutil.move(str(excel_file), str(dst))
                file_count['geografi'] += 1

        self.log(f"\n  ✓ Kommunalvalg: {file_count['kommunal']} filer")
        self.log(f"  ✓ Regionsrådsvalg: {file_count['regional']} filer")
        self.log(f"  ✓ Samlet data: {file_count['samlet']} filer")
        self.log(f"  ✓ Geografiske data: {file_count['geografi']} filer")
        self.log(f"  ✓ Valgdeltagelse Kommunal: {file_count['valgdelt_k']} filer")
        self.log(f"  ✓ Valgdeltagelse Regional: {file_count['valgdelt_r']} filer")

        self.log("\n✅ Filorganisering færdig")
        return True

    def print_summary(self):
        """Print pipeline summary"""
        elapsed = datetime.now() - self.start_time
        minutes = int(elapsed.total_seconds() // 60)
        seconds = int(elapsed.total_seconds() % 60)

        self.log("="*60)
        self.log("📊 PIPELINE SAMMENFATNING")
        self.log("="*60)
        self.log(f"⏱️  Samlet tid: {minutes}m {seconds}s")
        self.log(f"📁 Output: {self.output_dir.absolute()}")
        self.log(f"📝 Log fil: {self.log_file}")

        # Tjek output filer
        if self.output_dir.exists():
            xlsx_files = list(self.output_dir.glob('*.xlsx'))
            self.log(f"📄 Genererede Excel-filer: {len(xlsx_files)}")

            master_findings = self.output_dir / 'MASTER_FINDINGS.md'
            if master_findings.exists():
                self.log(f"✅ MASTER_FINDINGS.md genereret")

        self.log("="*60)
        self.log("✅ PIPELINE FÆRDIG!")
        self.log("="*60)

def main():
    parser = argparse.ArgumentParser(
        description='Valgdata Pipeline - Automatiseret data processing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Eksempler:
  python pipeline.py --all                    # Kør hele pipeline
  python pipeline.py --download --convert     # Kun download og konvertering
  python pipeline.py --clean --all            # Slet gamle filer og kør alt
  python pipeline.py --skip-download --all    # Brug eksisterende JSON
        """
    )

    parser.add_argument('--all', action='store_true',
                       help='Kør hele pipeline')
    parser.add_argument('--download', action='store_true',
                       help='Download JSON data')
    parser.add_argument('--convert', action='store_true',
                       help='Konverter JSON til Excel')
    parser.add_argument('--analyze', action='store_true',
                       help='Kør kønsanalyse')
    parser.add_argument('--findings', action='store_true',
                       help='Generer findings')
    parser.add_argument('--organize', action='store_true',
                       help='Organiser filer i mapper')
    parser.add_argument('--clean', action='store_true',
                       help='Slet gamle filer først')
    parser.add_argument('--skip-download', action='store_true',
                       help='Spring download over (brug eksisterende JSON)')
    parser.add_argument('--json-dir', default='json_data',
                       help='JSON directory (default: json_data)')
    parser.add_argument('--output-dir', default='excel_output',
                       help='Output directory (default: excel_output)')

    args = parser.parse_args()

    # Hvis ingen options, vis hjælp
    if not any([args.all, args.download, args.convert, args.analyze,
                args.findings, args.organize, args.clean]):
        parser.print_help()
        sys.exit(1)

    # Opret pipeline
    pipeline = Pipeline(args.json_dir, args.output_dir)

    print("""
╔══════════════════════════════════════════════════════════════╗
║                   VALGDATA PIPELINE 2025                     ║
║          Kommunal- og Regionsrådsvalg Analysis               ║
╚══════════════════════════════════════════════════════════════╝
""")

    pipeline.log("🚀 Starter pipeline...")

    success = True

    # Clean
    if args.clean:
        pipeline.clean()

    # Download
    if args.all and not args.skip_download:
        if not pipeline.download():
            success = False
    elif args.download:
        if not pipeline.download():
            success = False

    # Convert
    if (args.all or args.convert) and success:
        if not pipeline.convert():
            success = False

    # Analyze
    if (args.all or args.analyze) and success:
        if not pipeline.analyze_gender():
            success = False
        if not pipeline.analyze_general():
            success = False
        if not pipeline.analyze_borgmestre():
            success = False

    # Findings
    if (args.all or args.findings) and success:
        if not pipeline.generate_findings():
            success = False

    # Validate (altid efter findings)
    if (args.all or args.findings) and success:
        if not pipeline.validate_data():
            success = False
            pipeline.log("⚠️  ADVARSEL: Data validation fejlede - tjek output!", 'WARNING')

    # Organize
    if (args.all or args.organize) and success:
        if not pipeline.organize_files():
            success = False

    # Summary
    pipeline.print_summary()

    if not success:
        pipeline.log("❌ Pipeline fejlede", 'ERROR')
        sys.exit(1)

    sys.exit(0)

if __name__ == '__main__':
    main()
