#!/usr/bin/env python3
"""
Parser borgmestre.md og gemmer som struktureret CSV
Robust version med defensive checks og fejlhåndtering
"""

import re
import csv
from pathlib import Path
import sys

def validate_borgmester_entry(entry):
    """Valider at en borgmester-entry har de nødvendige felter"""
    if not entry.get('Kommune'):
        return False, "Mangler kommunenavn"
    if not entry.get('Navn'):
        return False, "Mangler borgmesternavn"
    if not entry.get('Status') or entry['Status'] not in ['Genvalgt', 'Magtskifte', 'Nyvalgt']:
        return False, f"Ugyldig status: {entry.get('Status')}"
    if entry.get('PersonligeStemmer', 0) < 0:
        return False, "Negative stemmer"
    return True, "OK"

def parse_borgmestre(input_file='borgmestre.md', output_file='borgmestre_parsed.csv'):
    """Parse borgmestre.md til struktureret CSV med defensive checks"""
    
    # Tjek at input-filen eksisterer
    if not Path(input_file).exists():
        print(f"❌ Fejl: Filen {input_file} findes ikke")
        return []

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Fejl ved læsning af {input_file}: {e}")
        return []

    lines = content.split('\n')
    borgmestre = []
    errors = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Find kommune navn (linje før "Valgt" eller "Ikke afgjort")
        if i + 1 < len(lines) and lines[i + 1].strip() in ['Valgt', 'Ikke afgjort']:
            kommune = line if line else None
            i += 1
            valgt_status = lines[i].strip()
            i += 1

            # Skip entries der ikke er valgt
            if valgt_status != 'Valgt':
                i += 1
                continue

            # Skip "Billede af" linje hvis den findes
            if i < len(lines) and lines[i].strip().startswith('Billede af'):
                i += 1

            # Navn (required)
            navn = None
            if i < len(lines) and lines[i].strip():
                navn_candidate = lines[i].strip()
                # Valider at det ligner et navn (ikke en status eller andet keyword)
                if navn_candidate not in ['Genvalgt', 'Magtskifte', 'Nyvalgt', 'Valgt', 'Ikke afgjort']:
                    navn = navn_candidate
                    i += 1
                else:
                    errors.append(f"Kunne ikke parse navn for {kommune}")
                    i += 1
                    continue
            else:
                errors.append(f"Mangler navn for {kommune}")
                i += 1
                continue

            # Status (Genvalgt/Magtskifte/Nyvalgt)
            status_type = ""
            if i < len(lines) and lines[i].strip() in ['Genvalgt', 'Magtskifte', 'Nyvalgt']:
                status_type = lines[i].strip()
                i += 1
            else:
                # Mangler status - prøv at gætte eller sæt til tomt
                if i < len(lines):
                    errors.append(f"Mangler eller ugyldig status for {navn} ({kommune}): {lines[i].strip()[:50]}")

            # Personlige stemmer
            personlige_stemmer = 0
            if i < len(lines):
                stemmer_line = lines[i].strip()
                match = re.search(r'(\d+[\.,]?\d*)\s+personlige stemmer', stemmer_line)
                if match:
                    try:
                        personlige_stemmer = int(match.group(1).replace('.', '').replace(',', ''))
                        i += 1
                    except ValueError as e:
                        errors.append(f"Kunne ikke parse stemmer for {navn}: {e}")
                        i += 1

            # Parti
            parti = ""
            if i < len(lines):
                next_line = lines[i].strip()
                # Tjek at det ikke er valgdato-linjen
                if next_line and not next_line.startswith('Valgt til borgmester'):
                    parti = next_line
                    i += 1

            # Valgdato og tidspunkt
            valgdato = ""
            valgtidspunkt = ""
            if i < len(lines) and lines[i].strip().startswith('Valgt til borgmester:'):
                dato_line = lines[i].strip()
                match = re.search(r'Valgt til borgmester:\s+(\d+\.\s+\w+)\s+([\d.]+)', dato_line)
                if match:
                    valgdato = match.group(1)
                    valgtidspunkt = match.group(2)
                i += 1

            # Valider og gem entry
            entry = {
                'Kommune': kommune or "Ukendt",
                'Navn': navn,
                'Status': status_type,
                'PersonligeStemmer': personlige_stemmer,
                'Parti': parti,
                'ValgDato': valgdato,
                'ValgTidspunkt': valgtidspunkt
            }

            is_valid, error_msg = validate_borgmester_entry(entry)
            if is_valid:
                borgmestre.append(entry)
            else:
                errors.append(f"Ugyldig entry for {navn or kommune}: {error_msg}")

        i += 1

    # Vis parsing errors hvis der er nogen
    if errors:
        print(f"\n⚠️  {len(errors)} parsing-advarsler:")
        for error in errors[:10]:  # Vis max 10 første fejl
            print(f"   • {error}")
        if len(errors) > 10:
            print(f"   ... og {len(errors) - 10} flere")

    # Gem til CSV
    if borgmestre:
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['Kommune', 'Navn', 'Status', 'PersonligeStemmer', 'Parti', 'ValgDato', 'ValgTidspunkt'])
                writer.writeheader()
                writer.writerows(borgmestre)

            print(f"\n✅ Parsede {len(borgmestre)} borgmestre")
            print(f"📁 Gemt til: {output_file}")

            # Vis kort statistik
            print(f"\n📊 Statistik:")
            print(f"   • Genvalgt: {sum(1 for b in borgmestre if b['Status'] == 'Genvalgt')}")
            print(f"   • Magtskifte: {sum(1 for b in borgmestre if b['Status'] == 'Magtskifte')}")
            print(f"   • Nyvalgt: {sum(1 for b in borgmestre if b['Status'] == 'Nyvalgt')}")

            return borgmestre
        except Exception as e:
            print(f"❌ Fejl ved skrivning af CSV: {e}")
            return []
    else:
        print("❌ Ingen gyldige borgmestre fundet")
        if errors:
            print("   Tjek parsing-advarsler ovenfor for detaljer")
        return []

def main(input_file='borgmestre.md', output_file='borgmestre_parsed.csv'):
    """Main funktion til brug i pipeline"""
    return parse_borgmestre(input_file, output_file)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Parse borgmestre.md til CSV')
    parser.add_argument('--input', default='borgmestre.md',
                       help='Input markdown fil (default: borgmestre.md)')
    parser.add_argument('--output', default='borgmestre_parsed.csv',
                       help='Output CSV fil (default: borgmestre_parsed.csv)')

    args = parser.parse_args()
    main(args.input, args.output)
