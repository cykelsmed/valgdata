#!/usr/bin/env python3
"""
Genbrugelige hjælpefunktioner til valgdata-projektet
"""

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
    - køn: 'M', 'K', eller 'Ukendt'
    - metode: 'manuel identifikation', 'AI-vurdering', eller 'gender-guesser'

    Prioritering:
    1. Manuel database (fra data/manuel_koen.json)
    2. gender-guesser automatisk estimering
    """
    if not fornavn or not isinstance(fornavn, str) or not fornavn.strip():
        return 'Ukendt', 'ingen_data'

    # Rens fornavn
    clean_name = fornavn.strip().split()[0]  # Tag kun første navn
    clean_name = clean_name.strip(',-.')  # Fjern special karakterer

    if not clean_name:
        return 'Ukendt', 'ingen_data'

    # 1. Tjek først i manuel database (højeste prioritet)
    manuel_data = load_gender_data()
    if clean_name in manuel_data:
        return manuel_data[clean_name], 'manuel identifikation'

    # 2. Brug gender-guesser som fallback
    try:
        result = _gender_detector.get_gender(clean_name, 'denmark')

        # Map resultater til M/K/Ukendt
        if result in ['male', 'mostly_male']:
            return 'M', 'gender-guesser'
        elif result in ['female', 'mostly_female']:
            return 'K', 'gender-guesser'
        elif result == 'andy':  # androgynous
            return 'Ukendt', 'gender-guesser (unisex)'
        else:  # unknown
            return 'Ukendt', 'gender-guesser (ukendt)'
    except Exception as e:
        return 'Ukendt', f'fejl: {str(e)}'


def find_latest_file(pattern):
    """Find den nyeste fil der matcher pattern"""
    files = glob.glob(pattern)
    if not files:
        return None
    # Sorter efter modificeringstid, nyeste først
    files.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)
    return files[0]


def save_parquet(df, filepath, description=""):
    """Gem DataFrame som Parquet med metadata"""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(filepath, engine='pyarrow', compression='snappy')
    if description:
        print(f"✓ {description}: {filepath.name} ({len(df)} rækker)")
    else:
        print(f"✓ Parquet gemt: {filepath.name} ({len(df)} rækker)")


def load_parquet(filepath):
    """Indlæs Parquet-fil"""
    return pd.read_parquet(filepath, engine='pyarrow')

