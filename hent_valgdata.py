#!/usr/bin/env python3
"""
Hent valgdata fra valg.dk SFTP-server
Download alle JSON-filer for kommunalvalg 2025

Brug: python hent_valgdata.py [output_mappe]
"""

import paramiko
from pathlib import Path
import sys


def hent_fra_sftp(output_mappe="./json_data"):
    """
    Forbind til SFTP og download alle JSON-filer.
    """
    # SFTP-oplysninger
    hostname = "data.valg.dk"
    port = 22
    username = "Valg"
    password = "Valg"

    output_path = Path(output_mappe)
    output_path.mkdir(exist_ok=True)

    print("=" * 60)
    print("VALG.DK SFTP Download")
    print("=" * 60)
    print(f"Forbinder til {hostname}...")

    # Opret SSH-klient
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Forbind til SFTP
        ssh.connect(hostname, port=port, username=username, password=password)
        sftp = ssh.open_sftp()
        print("Forbindelse oprettet!")

        # List rod-mappe
        print("\nUdforsker SFTP-server...")
        download_recursive(sftp, "/", output_path)

        sftp.close()
        ssh.close()

        print(f"\nDownload færdig! Filer gemt i: {output_path}")

    except paramiko.AuthenticationException:
        print("FEJL: Autentificering fejlede. Tjek brugernavn/password.")
    except paramiko.SSHException as e:
        print(f"FEJL: SSH-forbindelse fejlede: {e}")
    except Exception as e:
        print(f"FEJL: {e}")
        raise


def download_recursive(sftp, remote_path, local_path, indent=0):
    """
    Download filer rekursivt fra SFTP-server.
    """
    prefix = "  " * indent

    try:
        items = sftp.listdir_attr(remote_path)
    except Exception as e:
        print(f"{prefix}Kan ikke læse {remote_path}: {e}")
        return

    for item in items:
        remote_item = f"{remote_path}/{item.filename}".replace("//", "/")
        local_item = local_path / item.filename

        # Check om det er en mappe
        if stat_is_dir(item):
            print(f"{prefix}[MAPPE] {item.filename}/")
            local_item.mkdir(exist_ok=True)
            download_recursive(sftp, remote_item, local_item, indent + 1)
        else:
            # Download fil (kun JSON-filer)
            if item.filename.endswith(".json"):
                print(f"{prefix}  ↓ {item.filename} ({format_size(item.st_size)})")
                try:
                    sftp.get(remote_item, str(local_item))
                except Exception as e:
                    print(f"{prefix}    FEJL: {e}")
            else:
                print(f"{prefix}  - {item.filename} (springes over)")


def stat_is_dir(attr):
    """Check om SFTP-attribut er en mappe."""
    import stat
    return stat.S_ISDIR(attr.st_mode)


def format_size(size_bytes):
    """Formater filstørrelse til læsbar tekst."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def main():
    output_mappe = sys.argv[1] if len(sys.argv) > 1 else "./json_data"
    hent_fra_sftp(output_mappe)

    # Tæl downloadede filer
    json_filer = list(Path(output_mappe).rglob("*.json"))
    print(f"\nTotal: {len(json_filer)} JSON-filer hentet")

    if json_filer:
        print("\nNæste skridt:")
        print(f'  python valg_json_til_excel.py "{output_mappe}" "./excel_output"')


if __name__ == "__main__":
    main()
