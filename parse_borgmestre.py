#!/usr/bin/env python3
"""
Parser borgmestre.md og gemmer som struktureret CSV
"""

import re
import csv
from pathlib import Path

def parse_borgmestre(input_file='borgmestre.md', output_file='borgmestre_parsed.csv'):
    """Parse borgmestre.md til struktureret CSV"""

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split på blank linjer for at finde entries
    lines = content.split('\n')

    borgmestre = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Find kommune navn (linje før "Valgt" eller "Ikke afgjort")
        if i + 1 < len(lines) and lines[i + 1].strip() in ['Valgt', 'Ikke afgjort']:
            kommune = line
            i += 1
            valgt_status = lines[i].strip()
            i += 1

            # Skip "Billede af" linje
            if i < len(lines) and lines[i].strip().startswith('Billede af'):
                i += 1

            # Næste linje er navn
            if i < len(lines):
                navn = lines[i].strip()
                i += 1
            else:
                i += 1
                continue

            # Næste linje er Genvalgt/Magtskifte/Nyvalgt
            status_type = ""
            if i < len(lines) and lines[i].strip() in ['Genvalgt', 'Magtskifte', 'Nyvalgt']:
                status_type = lines[i].strip()
                i += 1

            # Næste linje er personlige stemmer
            personlige_stemmer = 0
            if i < len(lines):
                stemmer_line = lines[i].strip()
                match = re.search(r'(\d+[\.,]?\d*)\s+personlige stemmer', stemmer_line)
                if match:
                    personlige_stemmer = int(match.group(1).replace('.', '').replace(',', ''))
                    i += 1

            # Næste linje er parti
            parti = ""
            if i < len(lines) and not lines[i].strip().startswith('Valgt til borgmester'):
                parti = lines[i].strip()
                i += 1

            # Næste linje er valgdato
            valgdato = ""
            valgtidspunkt = ""
            if i < len(lines) and lines[i].strip().startswith('Valgt til borgmester:'):
                dato_line = lines[i].strip()
                match = re.search(r'Valgt til borgmester:\s+(\d+\.\s+\w+)\s+([\d.]+)', dato_line)
                if match:
                    valgdato = match.group(1)
                    valgtidspunkt = match.group(2)
                i += 1

            # Gem data hvis vi har et gyldigt navn
            if navn and valgt_status == 'Valgt':
                borgmestre.append({
                    'Kommune': kommune,
                    'Navn': navn,
                    'Status': status_type,
                    'PersonligeStemmer': personlige_stemmer,
                    'Parti': parti,
                    'ValgDato': valgdato,
                    'ValgTidspunkt': valgtidspunkt
                })

        i += 1

    # Gem til CSV
    if borgmestre:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['Kommune', 'Navn', 'Status', 'PersonligeStemmer', 'Parti', 'ValgDato', 'ValgTidspunkt'])
            writer.writeheader()
            writer.writerows(borgmestre)

        print(f"✅ Parsede {len(borgmestre)} borgmestre")
        print(f"📁 Gemt til: {output_file}")

        # Vis kort statistik
        print(f"\n📊 Statistik:")
        print(f"   • Genvalgt: {sum(1 for b in borgmestre if b['Status'] == 'Genvalgt')}")
        print(f"   • Magtskifte: {sum(1 for b in borgmestre if b['Status'] == 'Magtskifte')}")
        print(f"   • Nyvalgt: {sum(1 for b in borgmestre if b['Status'] == 'Nyvalgt')}")

        return borgmestre
    else:
        print("❌ Ingen borgmestre fundet")
        return []

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Parse borgmestre.md til CSV')
    parser.add_argument('--input', default='borgmestre.md',
                       help='Input markdown fil (default: borgmestre.md)')
    parser.add_argument('--output', default='borgmestre_parsed.csv',
                       help='Output CSV fil (default: borgmestre_parsed.csv)')

    args = parser.parse_args()
    parse_borgmestre(args.input, args.output)
