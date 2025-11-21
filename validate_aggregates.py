#!/usr/bin/env python3
"""
Aggregate-niveau validering af valgdata

Dette script validerer intern konsistens i valgdata:
- Stemme-balance per afstemningsområde
- Valgdeltagelse-beregninger
- Nationale totaler
- Parti-niveau aggregater
"""

import pandas as pd
from pathlib import Path
from utils import find_latest_file, load_parquet

# FORVENTEDE VÆRDIER FRA VALG.DK / OFFICIELLE KILDER
# Opdater disse værdier når de er tilgængelige
FORVENTEDE_NATIONALE_TOTALER = {
    'KOMMUNAL': {
        'Stemmeberettigede': 4784749,  # DR 2025-11-21
        'AfgivneStemmer': None,         # DR rapporterer ikke separat
        'GyldigeStemmer': 3256070,      # DR 2025-11-21
        'Valgdeltagelse': 69.2,         # DR 2025-11-21 (procent)
        # Kilde: https://www.dr.dk/nyheder/politik/kommunalvalg/resultater
    },
    'REGIONAL': {
        'Stemmeberettigede': None,
        'AfgivneStemmer': None,
        'GyldigeStemmer': None,
        'Valgdeltagelse': None,
    }
}

# Top 10 partier - forventede nationale totaler
# Kilde: https://www.altinget.dk/valgresultat2025/KV25/1
FORVENTEDE_PARTI_TOTALER = {
    'KOMMUNAL': {
        'Socialdemokratiet': 754304,                         # DR 2025-11-21 (23.2%)
        'Venstre, Danmarks Liberale Parti': 581495,          # DR 2025-11-21 (17.9%)
        'Det Konservative Folkeparti': 413546,               # DR 2025-11-21 (12.7%)
        'SF - Socialistisk Folkeparti': 360016,              # DR 2025-11-21 (11.1%)
        'Enhedslisten - De Rød-Grønne': 230404,              # DR 2025-11-21 (7.1%)
        'Dansk Folkeparti': None,                            # DR har ikke specifikt tal
        'Liberal Alliance': None,                            # DR: 5.5% men ikke absolut tal
        'Radikale Venstre': None,
        'Danmarksdemokraterne - Inger Støjberg': None,       # DR: 4.7%
        'Moderaterne': None,
        # Kilde: https://www.dr.dk/nyheder/politik/kommunalvalg/resultater
    },
    'REGIONAL': {
        'Socialdemokratiet': None,
        'Venstre, Danmarks Liberale Parti': None,
        'SF - Socialistisk Folkeparti': None,
        'Det Konservative Folkeparti': None,
        'Dansk Folkeparti': None,
        'Enhedslisten - De Rød-Grønne': None,
        'Radikale Venstre': None,
        'Liberal Alliance': None,
        'Danmarksdemokraterne - Inger Støjberg': None,
        'Moderaterne': None,
    }
}

class AggregateValidator:
    def __init__(self, valgtype='KOMMUNAL'):
        self.valgtype = valgtype
        self.df = self._load_data()
        self.errors = []
        self.warnings = []
        self.success_count = 0
        self.total_checks = 0

    def _load_data(self):
        """Load den nyeste valgresultater fil"""
        parquet_dir = Path('excel_output/parquet')
        res_fil = find_latest_file(str(parquet_dir / f'valgresultater_{self.valgtype}_*.parquet'))

        if not res_fil:
            raise FileNotFoundError(f"Kunne ikke finde valgresultater fil for {self.valgtype}")

        print(f"📖 Læser: {Path(res_fil).name}\n")
        return load_parquet(res_fil)

    def _check(self, condition, success_msg, error_msg):
        """Helper til at tjekke en condition og registrere resultat"""
        self.total_checks += 1
        if condition:
            self.success_count += 1
            print(f"   ✅ {success_msg}")
            return True
        else:
            self.errors.append(error_msg)
            print(f"   ❌ {error_msg}")
            return False

    def _warn(self, condition, warning_msg):
        """Helper til at give en advarsel"""
        if not condition:
            self.warnings.append(warning_msg)
            print(f"   ⚠️  {warning_msg}")

    def validate_stemme_balance(self):
        """Valider at stemme-balance stemmer per afstemningsområde"""
        print("="*80)
        print("1. STEMME-BALANCE VALIDERING")
        print("="*80)

        # Dedupliker til afstemningsområde-niveau
        areas = self.df.groupby('AfstemningsområdeDagiId').first().reset_index()

        print(f"\n📊 Analyserer {len(areas)} afstemningsområder...")

        # Beregn summen af alle partiers stemmer per område
        parti_stemmer = self.df.groupby(['AfstemningsområdeDagiId', 'ListeNavn'])['ListeStemmer'].first()
        parti_stemmer_sum = parti_stemmer.groupby('AfstemningsområdeDagiId').sum().reset_index()
        parti_stemmer_sum.columns = ['AfstemningsområdeDagiId', 'SumPartiStemmer']

        # Merge med areas
        areas = areas.merge(parti_stemmer_sum, on='AfstemningsområdeDagiId')

        # Tjek 1: GyldigeStemmer = sum af alle parti-stemmer
        areas['Difference_Gyldige'] = areas['GyldigeStemmer'] - areas['SumPartiStemmer']
        max_diff = areas['Difference_Gyldige'].abs().max()

        self._check(
            max_diff < 1,
            f"GyldigeStemmer matcher sum af parti-stemmer (max afvigelse: {max_diff})",
            f"GyldigeStemmer matcher IKKE sum af parti-stemmer (max afvigelse: {max_diff})"
        )

        # Tjek 2: AfgivneStemmer = GyldigeStemmer + UgyldigeStemmer + BlankeStemmer
        areas['Beregnet_Afgivne'] = areas['GyldigeStemmer'] + areas['UgyldigeStemmer'] + areas['BlankeStemmer']
        areas['Difference_Afgivne'] = areas['AfgivneStemmer'] - areas['Beregnet_Afgivne']
        max_diff_afgivne = areas['Difference_Afgivne'].abs().max()

        self._check(
            max_diff_afgivne < 1,
            f"AfgivneStemmer matcher GyldigeStemmer + UgyldigeStemmer + BlankeStemmer (max afvigelse: {max_diff_afgivne})",
            f"AfgivneStemmer matcher IKKE (max afvigelse: {max_diff_afgivne})"
        )

        # Tjek 3: Valgdeltagelse beregning
        areas['Beregnet_Valgdeltagelse'] = (areas['AfgivneStemmer'] / areas['Stemmeberettigede'] * 100).round(2)
        areas['Difference_Valgdeltagelse'] = (areas['ValgdeltagelseProcent'] - areas['Beregnet_Valgdeltagelse']).abs()
        max_diff_valgdelt = areas['Difference_Valgdeltagelse'].max()

        self._check(
            max_diff_valgdelt < 0.1,
            f"Valgdeltagelse beregnet korrekt (max afvigelse: {max_diff_valgdelt:.3f}%)",
            f"Valgdeltagelse beregning FEJLER (max afvigelse: {max_diff_valgdelt:.3f}%)"
        )

        # Vis områder med afvigelser hvis der er nogen
        if max_diff >= 1 or max_diff_afgivne >= 1:
            print(f"\n   ⚠️  Områder med afvigelser:")
            problemer = areas[
                (areas['Difference_Gyldige'].abs() >= 1) |
                (areas['Difference_Afgivne'].abs() >= 1)
            ]
            for _, row in problemer.head(5).iterrows():
                print(f"      {row['Afstemningsområde']}: Gyldige diff={row['Difference_Gyldige']}, Afgivne diff={row['Difference_Afgivne']}")

    def validate_data_quality(self):
        """Valider data kvalitet - ingen negative tal, outliers, etc."""
        print("\n" + "="*80)
        print("2. DATA KVALITETS-VALIDERING")
        print("="*80)

        print(f"\n📊 Analyserer {len(self.df)} datarækker...")

        # Tjek for negative værdier
        numeric_cols = ['Stemmeberettigede', 'AfgivneStemmer', 'GyldigeStemmer',
                        'UgyldigeStemmer', 'BlankeStemmer', 'PersonligeStemmer', 'ListeStemmer']

        for col in numeric_cols:
            if col in self.df.columns:
                negative_count = (self.df[col] < 0).sum()
                self._check(
                    negative_count == 0,
                    f"Ingen negative værdier i {col}",
                    f"FUNDET {negative_count} negative værdier i {col}"
                )

        # Tjek valgdeltagelse range
        areas = self.df.groupby('AfstemningsområdeDagiId')['ValgdeltagelseProcent'].first()
        min_valgdelt = areas.min()
        max_valgdelt = areas.max()

        self._check(
            min_valgdelt >= 0 and max_valgdelt <= 100,
            f"Valgdeltagelse inden for 0-100% (range: {min_valgdelt:.1f}% - {max_valgdelt:.1f}%)",
            f"Valgdeltagelse UDEN FOR range 0-100%: {min_valgdelt:.1f}% - {max_valgdelt:.1f}%"
        )

        # Advarsel om meget lav eller meget høj valgdeltagelse
        self._warn(
            min_valgdelt >= 30,
            f"Meget lav valgdeltagelse fundet: {min_valgdelt:.1f}%"
        )
        self._warn(
            max_valgdelt <= 95,
            f"Meget høj valgdeltagelse fundet: {max_valgdelt:.1f}%"
        )

        # Tjek for duplikater (bør ikke eksistere efter deduplikering)
        dupes = self.df.duplicated(subset=['AfstemningsområdeDagiId', 'KandidatId']).sum()
        self._check(
            dupes == 0,
            f"Ingen duplikater fundet (AfstemningsområdeDagiId + KandidatId)",
            f"FUNDET {dupes} duplikater!"
        )

    def validate_nationale_totaler(self):
        """Valider nationale totaler"""
        print("\n" + "="*80)
        print("3. NATIONALE TOTALER")
        print("="*80)

        # Dedupliker til afstemningsområde-niveau
        areas = self.df.groupby('AfstemningsområdeDagiId').first().reset_index()

        # Beregn totaler
        total_stemmeberettigede = areas['Stemmeberettigede'].sum()
        total_afgivne = areas['AfgivneStemmer'].sum()
        total_gyldige = areas['GyldigeStemmer'].sum()
        total_ugyldige = areas['UgyldigeStemmer'].sum()
        total_blanke = areas['BlankeStemmer'].sum()

        national_valgdeltagelse = (total_afgivne / total_stemmeberettigede * 100)

        print(f"\n📊 Beregnede nationale totaler ({self.valgtype}):")
        print(f"   Stemmeberettigede:  {total_stemmeberettigede:>12,}")
        print(f"   Afgivne stemmer:    {total_afgivne:>12,}")
        print(f"   Gyldige stemmer:    {total_gyldige:>12,}")
        print(f"   Ugyldige stemmer:   {total_ugyldige:>12,}")
        print(f"   Blanke stemmer:     {total_blanke:>12,}")
        print(f"   Valgdeltagelse:     {national_valgdeltagelse:>12.2f}%")

        # Sammenlign med forventede værdier hvis tilgængelige
        forventede = FORVENTEDE_NATIONALE_TOTALER.get(self.valgtype, {})

        if any(v is not None for v in forventede.values()):
            print(f"\n📊 Sammenligning med valg.dk:")

            if forventede.get('Stemmeberettigede') is not None:
                diff = total_stemmeberettigede - forventede['Stemmeberettigede']
                pct_diff = (diff / forventede['Stemmeberettigede'] * 100) if forventede['Stemmeberettigede'] > 0 else 0
                self._check(
                    abs(pct_diff) < 0.1,
                    f"Stemmeberettigede matcher (diff: {diff:,}, {pct_diff:.3f}%)",
                    f"Stemmeberettigede MATCHER IKKE (diff: {diff:,}, {pct_diff:.3f}%)"
                )

            if forventede.get('AfgivneStemmer') is not None:
                diff = total_afgivne - forventede['AfgivneStemmer']
                pct_diff = (diff / forventede['AfgivneStemmer'] * 100) if forventede['AfgivneStemmer'] > 0 else 0
                self._check(
                    abs(pct_diff) < 0.1,
                    f"AfgivneStemmer matcher (diff: {diff:,}, {pct_diff:.3f}%)",
                    f"AfgivneStemmer MATCHER IKKE (diff: {diff:,}, {pct_diff:.3f}%)"
                )

            if forventede.get('GyldigeStemmer') is not None:
                diff = total_gyldige - forventede['GyldigeStemmer']
                pct_diff = (diff / forventede['GyldigeStemmer'] * 100) if forventede['GyldigeStemmer'] > 0 else 0
                self._check(
                    abs(pct_diff) < 0.1,
                    f"GyldigeStemmer matcher (diff: {diff:,}, {pct_diff:.3f}%)",
                    f"GyldigeStemmer MATCHER IKKE (diff: {diff:,}, {pct_diff:.3f}%)"
                )

            if forventede.get('Valgdeltagelse') is not None:
                diff = national_valgdeltagelse - forventede['Valgdeltagelse']
                self._check(
                    abs(diff) < 0.1,
                    f"Valgdeltagelse matcher (diff: {diff:.3f}%)",
                    f"Valgdeltagelse MATCHER IKKE (diff: {diff:.3f}%)"
                )
        else:
            print(f"\n   ℹ️  For at validere mod valg.dk: Tilføj officielle værdier til scriptet")

    def validate_parti_totaler(self, top_n=10):
        """Valider parti-niveau aggregater"""
        print("\n" + "="*80)
        print(f"4. TOP {top_n} PARTIER - NATIONALE TOTALER")
        print("="*80)

        # Dedupliker ListeStemmer per område per parti
        parti_per_omraade = self.df.groupby(['AfstemningsområdeDagiId', 'ListeNavn'])['ListeStemmer'].first()

        # Summer på tværs af alle områder
        parti_totaler = parti_per_omraade.groupby('ListeNavn').sum().sort_values(ascending=False)

        print(f"\n📊 Top {top_n} partier ({self.valgtype}):\n")
        for i, (parti, stemmer) in enumerate(parti_totaler.head(top_n).items(), 1):
            print(f"   {i:2d}. {parti:45s} {stemmer:>10,} stemmer")

        # Beregn også fordeling af personlige vs liste-stemmer
        print(f"\n📊 Personlige vs Listestemmer breakdown:\n")

        personlige_total = self.df.groupby('ListeNavn')['PersonligeStemmer'].sum()
        listestemmer_dedupe = self.df.groupby(['AfstemningsområdeDagiId', 'ListeNavn'])['Listestemmer'].first()
        listestemmer_total = listestemmer_dedupe.groupby('ListeNavn').sum()

        for parti in parti_totaler.head(5).index:
            personlige = personlige_total.get(parti, 0)
            liste = listestemmer_total.get(parti, 0)
            total = personlige + liste
            pct_personlige = (personlige / total * 100) if total > 0 else 0

            print(f"   {parti[:40]:40s}")
            print(f"      Personlige: {personlige:>10,} ({pct_personlige:5.1f}%)")
            print(f"      Liste:      {liste:>10,} ({100-pct_personlige:5.1f}%)")
            print(f"      Total:      {total:>10,}")

        # Sammenlign med forventede værdier hvis tilgængelige
        forventede_partier = FORVENTEDE_PARTI_TOTALER.get(self.valgtype, {})

        if any(v is not None for v in forventede_partier.values()):
            print(f"\n📊 Sammenligning med DR/Altinget:")

            for parti, forventet_stemmer in forventede_partier.items():
                if forventet_stemmer is not None and parti in parti_totaler.index:
                    vores_stemmer = parti_totaler[parti]
                    diff = vores_stemmer - forventet_stemmer
                    pct_diff = (diff / forventet_stemmer * 100) if forventet_stemmer > 0 else 0

                    self._check(
                        abs(pct_diff) < 0.5,
                        f"{parti[:35]:35s} matcher (diff: {diff:>7,}, {pct_diff:>6.2f}%)",
                        f"{parti[:35]:35s} MATCHER IKKE (diff: {diff:>7,}, {pct_diff:>6.2f}%)"
                    )
        else:
            print(f"\n   ℹ️  For at validere mod DR/Altinget: Tilføj forventede værdier til scriptet")

    def print_summary(self):
        """Print sammenfatning af validering"""
        print("\n\n" + "="*80)
        print("📋 VALIDERINGS-SAMMENFATNING")
        print("="*80)

        success_rate = (self.success_count / self.total_checks * 100) if self.total_checks > 0 else 0

        print(f"\n   Total checks:    {self.total_checks}")
        print(f"   Succesfulde:     {self.success_count}")
        print(f"   Fejl:            {len(self.errors)}")
        print(f"   Advarsler:       {len(self.warnings)}")
        print(f"   Success rate:    {success_rate:.1f}%")

        if self.errors:
            print(f"\n   ❌ FEJL FUNDET:")
            for error in self.errors:
                print(f"      • {error}")

        if self.warnings:
            print(f"\n   ⚠️  ADVARSLER:")
            for warning in self.warnings:
                print(f"      • {warning}")

        if len(self.errors) == 0:
            print(f"\n   ✅ ALLE INTERNE KONSISTENS-TJEK BESTÅET!")
        else:
            print(f"\n   ⚠️  Der blev fundet {len(self.errors)} fejl - undersøg nærmere")

        print(f"\n{'='*80}\n")

def main():
    print("="*80)
    print("AGGREGATE-NIVEAU VALIDERING AF VALGDATA")
    print("="*80)

    # Valider kommunalvalg
    print("\n🏛️  KOMMUNALVALG\n")
    validator_kommunal = AggregateValidator('KOMMUNAL')
    validator_kommunal.validate_stemme_balance()
    validator_kommunal.validate_data_quality()
    validator_kommunal.validate_nationale_totaler()
    validator_kommunal.validate_parti_totaler(top_n=10)
    validator_kommunal.print_summary()

    # Valider regionsrådsvalg
    print("\n🏛️  REGIONSRÅDSVALG\n")
    validator_regional = AggregateValidator('REGIONAL')
    validator_regional.validate_stemme_balance()
    validator_regional.validate_data_quality()
    validator_regional.validate_nationale_totaler()
    validator_regional.validate_parti_totaler(top_n=10)
    validator_regional.print_summary()

if __name__ == '__main__':
    main()
