#!/usr/bin/env python3
"""
Data Validation - Sanity checks for valgdata
Sikrer at beregninger giver realistiske resultater
"""

import pandas as pd
from pathlib import Path
import sys

class ValidationError(Exception):
    """Exception raised when validation fails"""
    pass

class DataValidator:
    """Validerer valgdata for realistiske værdier"""

    # Realistiske grænser for Danmark (kommunal + regional combined)
    MAX_TOTAL_VOTES = 15_000_000  # Max ~15 mio stemmer (begge valg, listestemmer + personlige)
    MAX_VOTES_PER_PARTY = 3_000_000  # Max stemmer til ét parti (begge valg)
    MAX_PERSONAL_VOTES_CANDIDATE = 100_000  # Max personlige stemmer til én kandidat
    MIN_TURNOUT = 40.0  # Min valgdeltagelse %
    MAX_TURNOUT = 100.0  # Max valgdeltagelse %
    MAX_CANDIDATES = 15_000  # Max antal kandidater

    def __init__(self, output_dir='excel_output'):
        self.output_dir = Path(output_dir)
        self.errors = []
        self.warnings = []

    def validate_all(self):
        """Kør alle valideringer"""
        print("🔍 Validerer data...")

        try:
            self.validate_partistatistik()
            self.validate_stemmeslugere()
            self.validate_valgdeltagelse()
            self.validate_kandidat_antal()

            if self.errors:
                print("\n❌ VALIDERINGSFEJL FUNDET:")
                for error in self.errors:
                    print(f"  • {error}")
                return False

            if self.warnings:
                print("\n⚠️  ADVARSLER:")
                for warning in self.warnings:
                    print(f"  • {warning}")

            print("\n✅ Alle valideringer bestået!")
            return True

        except FileNotFoundError as e:
            print(f"❌ Kunne ikke finde fil: {e}")
            return False
        except Exception as e:
            print(f"❌ Uventet fejl under validering: {e}")
            return False

    def validate_partistatistik(self):
        """Valider partistatistik - tjek for overtællinger"""
        print("  • Validerer partistatistik...")

        # Find fil
        fil = self.output_dir / '00_START_HER' / 'Analyse_generel.xlsx'
        if not fil.exists():
            self.errors.append(f"Mangler fil: {fil}")
            return

        df = pd.read_excel(fil, sheet_name='Partistatistik')

        # Check totale stemmer
        total_stemmer = df['Totale Stemmer'].sum()
        if total_stemmer > self.MAX_TOTAL_VOTES:
            self.errors.append(
                f"Total stemmer ({total_stemmer:,}) overstiger max ({self.MAX_TOTAL_VOTES:,}). "
                f"Sandsynligvis overtælling af listestemmer!"
            )

        # Check individuelle partier
        for _, row in df.iterrows():
            parti = row['Parti']
            stemmer = row['Totale Stemmer']
            if stemmer > self.MAX_VOTES_PER_PARTY:
                self.errors.append(
                    f"{parti} har {stemmer:,} stemmer - over max ({self.MAX_VOTES_PER_PARTY:,})"
                )

        # Check stemmer per kandidat (skal være realistisk)
        for _, row in df.iterrows():
            parti = row['Parti']
            spm_kand = row['Stemmer per Kandidat']
            if spm_kand > 10_000:
                self.warnings.append(
                    f"{parti} har {spm_kand:,.0f} stemmer/kandidat - usædvanligt højt"
                )

        print(f"    ✓ Total stemmer: {total_stemmer:,}")

    def validate_stemmeslugere(self):
        """Valider top stemmeslugere"""
        print("  • Validerer stemmeslugere...")

        fil = self.output_dir / '00_START_HER' / 'Analyse_generel.xlsx'
        if not fil.exists():
            return

        df = pd.read_excel(fil, sheet_name='Top 100 Stemmeslugere')

        # Check top kandidat
        top_stemmer = df.iloc[0]['Personlige Stemmer']
        top_navn = df.iloc[0]['Navn']

        if top_stemmer > self.MAX_PERSONAL_VOTES_CANDIDATE:
            self.errors.append(
                f"Top kandidat {top_navn} har {top_stemmer:,} personlige stemmer - "
                f"over max ({self.MAX_PERSONAL_VOTES_CANDIDATE:,})"
            )

        # Check at personlige stemmer falder (er sorteret)
        if not df['Personlige Stemmer'].is_monotonic_decreasing:
            self.warnings.append("Stemmeslugere er ikke sorteret korrekt")

        print(f"    ✓ Top stemmemodtager: {top_navn} med {top_stemmer:,} stemmer")

    def validate_valgdeltagelse(self):
        """Valider valgdeltagelse procenter"""
        print("  • Validerer valgdeltagelse...")

        fil = self.output_dir / '00_START_HER' / 'Analyse_generel.xlsx'
        if not fil.exists():
            return

        df = pd.read_excel(fil, sheet_name='Valgdeltagelse')

        # Check procenter er realistiske
        min_pct = df['Valgdeltagelse %'].min()
        max_pct = df['Valgdeltagelse %'].max()
        avg_pct = df['Valgdeltagelse %'].mean()

        if min_pct < self.MIN_TURNOUT:
            self.warnings.append(
                f"Laveste valgdeltagelse ({min_pct:.1f}%) er usædvanligt lav"
            )

        if max_pct > self.MAX_TURNOUT:
            self.errors.append(
                f"Højeste valgdeltagelse ({max_pct:.1f}%) over 100%!"
            )

        if avg_pct < 50.0:
            self.warnings.append(
                f"Gennemsnitlig valgdeltagelse ({avg_pct:.1f}%) er lav"
            )

        print(f"    ✓ Valgdeltagelse: {min_pct:.1f}% - {max_pct:.1f}% (snit: {avg_pct:.1f}%)")

    def validate_kandidat_antal(self):
        """Valider antal kandidater"""
        print("  • Validerer kandidat-antal...")

        # Find kandidat-fil
        samlet_dir = self.output_dir / '03_Samlet_Alle_Valg'
        parquet_dir = self.output_dir / 'parquet'

        kandidat_fil = None
        for p in [parquet_dir / 'kandidater_ALLE_VALG_*.parquet',
                  samlet_dir / 'kandidater_ALLE_VALG_*.xlsx']:
            files = list(Path(p.parent).glob(p.name))
            if files:
                kandidat_fil = files[0]
                break

        if not kandidat_fil:
            self.warnings.append("Kunne ikke finde kandidat-fil til validering")
            return

        # Læs kandidater
        if kandidat_fil.suffix == '.parquet':
            df = pd.read_parquet(kandidat_fil)
        else:
            df = pd.read_excel(kandidat_fil)

        antal_kandidater = len(df)

        if antal_kandidater > self.MAX_CANDIDATES:
            self.warnings.append(
                f"Antal kandidater ({antal_kandidater:,}) virker højt"
            )

        if antal_kandidater < 1000:
            self.warnings.append(
                f"Antal kandidater ({antal_kandidater:,}) virker lavt"
            )

        print(f"    ✓ Antal kandidater: {antal_kandidater:,}")

def main():
    """Kør validering"""
    import argparse
    parser = argparse.ArgumentParser(description='Valider valgdata')
    parser.add_argument('--output-dir', default='excel_output', help='Output directory')
    args = parser.parse_args()

    validator = DataValidator(args.output_dir)
    success = validator.validate_all()

    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
