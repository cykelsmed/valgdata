#!/usr/bin/env python3
"""
Konvertering af valg.dk JSON-filer til Excel
Håndterer nested JSON-strukturer fra SFTP-serveren

Brug: python valg_json_til_excel.py <json_mappe> <output_mappe>
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys
import gender_guesser.detector as gender

# Initialiser gender detector
_gender_detector = gender.Detector()

# Manuel kønsbestemmelse database (prioriteres over automatisk gætning)
# Opdateret med 1151 manuelt + AI-identificerede kandidater (903 manuel + 248 AI = 597 unikke navne)
MANUEL_KØNSBESTEMMELSE = {
    # AI-vurderede kandidater (248 fra AI-vurdering)
    "Sønnik": "K", "Tais": "M", "Tayo": "K", "Tharjan": "M", "Tordur": "M",
    "Tune": "K", "Tórhallur": "M", "Ulrick": "M", "Vandad": "M", "Vichy": "K",
    "Wakas": "M", "Waris": "M", "Xinwei": "K", "Yalcin": "M", "Yildiz": "K",
    "Yilmaz": "M", "Yurdal": "M", "Ziggy": "K", "Zinije": "K", "Oruc": "M",
    "Ravin": "M", "Siff": "K", "Sven-Erik": "M", "Abaz": "M", "Aki": "M",
    "Aladdin": "M", "Almaz": "K", "Almin": "M", "Andries": "M", "Anje": "K",
    "Araz": "M", "Azad": "M", "Babak": "M", "Bauke": "M", "Benno": "M",
    "Bess": "K", "Birol": "M", "Bret": "M", "Bünyamin": "M", "Camillo": "M",
    "Candice": "K", "Celal": "M", "Christoph": "M", "Christophe": "M", "Clair": "K",
    "Cliff": "M", "Clément": "M", "Costel": "M", "Davíð": "M", "Dino": "M",
    "Dragoljub": "M", "Duygu": "K", "Eddy": "M", "Edibe": "K", "Edin": "M",
    "Edis": "M", "Edris": "M", "Eik": "M", "El": "M", "El Hamlaoui": "M", "Emely": "K",
    "Emin": "M", "Erdal": "M", "Ergin": "M", "Erkan": "M", "Esat": "M",
    "Eske": "M", "Estrid": "K", "Evis": "M", "Farid": "M", "Fatih": "M",
    "Fayez": "M", "Fedai": "M", "Filiz": "K", "Florian": "M", "Frans": "M",
    "Furkan": "M", "Gennadiy": "M", "Gunde": "M", "Gül": "K", "Günay": "K",
    "Halil": "M", "Hameed": "M", "Hamid": "M", "Hari": "M", "Hartmut": "M",
    "Hasibe": "K", "Hauke": "M", "Hediye": "K", "Heinrich": "M", "Helin": "K",
    "Henrich": "M", "Hermod": "M", "Hüseyin": "M", "Idrees": "M", "Idris": "M",
    "Ikram": "K", "Ilias": "M", "Imad": "M", "Ingalill": "K", "Isabell": "K",
    "Iulian": "M", "Ivonne": "K", "Jakup": "M", "Jari": "M", "Jarl": "M",
    "Joanne": "K", "Josée": "K", "João": "M", "Jóhannes": "M", "Kais": "M",
    "Kalle": "M", "Karan": "M", "Karel": "M", "Kashif": "M", "Katri": "K",
    "Khaled": "M", "Kiki": "K", "Kirsti": "K", "Kjartan": "M", "Käthe": "K",
    "Lennarth": "M", "Lianne": "K", "Lil": "K", "Lin": "K", "Luc": "M",
    "Magni": "K", "Mahmut": "M", "Marek": "M", "Margreet": "K", "Maricel": "K",
    "Marjan": "K", "Masoud": "M", "Mazlum": "M", "Meho": "M", "Menderes": "M",
    "Mercedes": "K", "Metin": "M", "Mevlide": "K", "Michel": "M", "Michele": "M",
    "Mick": "M", "Micky": "M", "Miki": "K", "Nadeem": "M", "Najib": "M",
    "Narcis": "M", "Nazim": "M", "Necdet": "M", "Nels": "M", "Nikki": "K",
    "Nini": "K", "Nino": "M", "Osman": "M", "Ozan": "M", "Parvaneh": "K",
    "Philipp": "M", "Piet": "M", "Pil": "K", "Rajesh": "M", "Ramalingam": "M",
    "Rami": "M", "Reinhold": "M", "Reinout": "M", "Renate": "K", "Renée": "K",
    "Resul": "M", "Ricco": "M", "Ricki": "M", "Rik": "M", "Saad": "M",
    "Sadik": "M", "Saime": "K", "Sami": "M", "Samir": "M", "Scarlett": "K",
    "Selene": "K", "Selim": "M", "Semir": "M", "Senol": "M", "Serdal": "M",
    "Serhat": "M", "Serhii": "M", "Seyit": "M", "Shukri": "K", "Siem": "M",
    "Sif": "K", "Silke": "K", "Steffan": "M", "Stoil": "M", "Suzan": "K",
    "Süleyman": "M", "Tao": "M", "Thilo": "M", "Thormod": "M", "Thure": "M",
    "Tilde": "K", "Timm": "M", "Timo": "M", "Tomislav": "M", "Tuncay": "M",
    "Turan": "M", "Uwe": "M", "Valentin": "M", "Vick": "K", "Yakup": "M",
    "Yasir": "M", "Yavuz": "M", "Yazmin": "K", "Özcan": "M", "Andi": "M",
    "Ludwig": "M", "Sadek": "M", "Ahmad": "M",
    # Manuelt identificerede kandidater (903 fra manuel identifikation = 597 unikke navne)
    "Abdinoor": "M", "Abdirashid": "M", "Abdul": "M", "Absalon": "M", "Adeel": "M",
    "Adnan": "M", "Adrian-Silviu": "M", "Aein": "K", "Agata": "K", "Ahmed": "M",
    "Ahmet": "M", "Ahn": "K", "Ajâja": "K", "Akhlaq": "M", "Alaaidin": "M",
    "Aleksander": "M", "Aleksandra": "K", "Ali": "M", "Alia": "M", "Aligo": "M",
    "Alina": "M", "Almina": "K", "Almind": "M", "Alvin": "M", "Amos": "M",
    "Amran": "K", "Anahita": "K", "Anastasia": "K", "Andeers": "M", "Ane-Jette": "K",
    "Aneken": "K", "Anes": "K", "Anfinn": "M", "Angelica": "K", "Angus": "M",
    "Aniska": "K", "Ann-Britt": "K", "Ann-Christina": "K", "Ann-Kathrine": "K", "Ann-Louise": "K",
    "Ann-Sophie": "K", "Anna-Cecilie": "K", "Anna-Mette": "K", "Anna-Sofie": "K", "Annbritt": "K",
    "Anne-Dorrit": "K", "Anne-Emmanuelle": "K", "Anne-Grete": "K", "Anne-Grethe": "K", "Anne-Lise": "K",
    "Anne-Marie": "K", "Anne-Mette": "K", "Anne-Sofie": "K", "Anne-Sophie": "K", "Annedorthe": "K",
    "Annegrete": "K", "Annemaja": "K", "Annet": "K", "Annia": "K", "Annitta": "K",
    "Anstina": "K", "Antoniett": "M", "Aqqalooraq": "M", "Arnbjørn": "M", "Arthur": "M",
    "Arulanantharajah": "K", "Asghar": "M", "Asham": "K", "Ashwini": "K", "Aslak": "M",
    "Asmus": "M", "Asou": "M", "Assia": "K", "Aston": "M", "Augusta": "K",
    "Auli": "K", "Aurin": "M", "Awale": "M", "Azra": "K", "Bakhtiar": "M",
    "Baltser": "M", "Bayram": "M", "Beatrice": "K", "Beenamol": "K", "Bella": "K",
    "Bergur": "M", "Bertram": "M", "Betiel": "K", "Bia": "K", "Bianca": "K",
    "Biljana": "K", "Bill": "M", "Billal": "M", "Bob": "M", "Bojanna": "M",
    "Burak": "M", "Bøje": "M", "Carl-Børge": "M", "Carl-Eric": "M", "Carl-Erik": "M",
    "Carli": "M", "Carol": "K", "Caspar": "M", "Cassandra": "K", "Catherine": "K",
    "Cecer": "K", "Celine": "K", "Cevri": "M", "Chano": "M", "Charlie": "M",
    "Chastine": "K", "Chelina": "K", "Chelle": "K", "Chili": "K", "Chirie": "K",
    "Chresta": "K", "Chriistofer": "M", "Christiane": "M", "Christopher": "M", "Cille": "K",
    "Cirkeline": "K", "Cita": "K", "Claude-Francois": "M", "Claus-Jørgen": "M", "Coco": "K",
    "Colin": "M", "Conrad": "M", "Court": "M", "Cömert": "M", "Damian": "M",
    "Danielle": "M", "Dann": "M", "Daphne": "K", "Dean": "M", "Debbie": "K",
    "Deborah": "K", "Dejla": "K", "Deniz": "K", "Derya": "K", "Desalegn": "M",
    "Desislava": "K", "Diana": "K", "Diane": "K", "Dickte": "K", "Dinos": "M",
    "Dion": "M", "Dirk-Ingmar": "M", "Dogan": "M", "Don": "M", "Dorete": "K",
    "Doron": "M", "Edisa": "K", "Ejler": "M", "Ektaj": "M", "Elanur": "K",
    "Elena": "K", "Elias": "M", "Eliska": "K", "Ellie": "K", "Else-Marie": "K",
    "Elsemarie": "K", "Emery": "M", "Emilia": "K", "Emiline": "K", "Emilla": "K",
    "Emilly": "K", "Emmanuel": "K", "Emrah": "M", "Enyah": "K", "Evals": "K",
    "Eyrun": "K", "Faghir": "K", "Fahreta": "K", "Faiza": "K", "Falle": "M",
    "Fasael": "M", "Fatma": "K", "Felex": "M", "Filip": "M", "Filippa": "M",
    "Fiona": "K", "Firat": "M", "Florina": "K", "Frands": "M", "Frederikke": "M",
    "Friis": "M", "Gabriel": "M", "Ganeswaran": "M", "Ganna": "K", "George": "M",
    "Gerthie": "K", "Githa": "K", "Godette": "K", "Gorget": "M", "Gregers": "M",
    "Gøye": "K", "Hajg": "M", "Hakan": "M", "Hakon": "M", "Hanna-Maria": "K",
    "Hans-Christian": "M", "Hans-Erhard": "M", "Hans-Henning": "M", "Hans-Henrik": "M", "Hans-Iver": "M",
    "Hans-Jørgen": "M", "Hans-Kristian": "M", "Hans-Ulrik": "M", "Harun": "M", "Harvey": "M",
    "Hassan": "M", "Hector": "M", "Hekla": "K", "Hella": "K", "Hellen": "K",
    "Hjalte": "M", "Holly": "K", "Huda": "K", "Ian": "M", "Ibrahim": "M",
    "Ida-Sofie": "K", "Ilka": "K", "Illa": "K", "Imadur": "M", "Imee": "K",
    "Inette": "K", "Inge-Lise": "K", "Inger-Lise": "K", "Inger-Margrethe": "K", "Inger-Marie": "K",
    "Ingred": "K", "Injam": "M", "Irem": "K", "Irvin": "M", "Isabel": "K",
    "Isabella": "K", "Ismail": "M", "Isminur": "K", "Iza": "K", "Jackie": "K",
    "Jacqueline": "K", "Jamal": "M", "Jamie": "M", "Jan-Erik": "M", "Janek": "M",
    "Janet": "M", "Jannich": "M", "Jannick": "M", "Jasmin": "K", "Jasminka": "K",
    "Jean-Louis": "M", "Jenees": "M", "Jennifer": "K", "Jens-Bernhard": "M", "Jens-Christian": "M",
    "Jens-Erik": "M", "Jens-Jørn": "M", "Jens-Kristian": "M", "Jens-Otto": "M", "Jens-Peter": "M",
    "Jensa": "M", "Jerrik": "M", "Jette-Kirsten": "K", "Jeyarajah": "K", "Jiesper": "M",
    "Jilali": "M", "Joacchim": "M", "Joanna": "K", "Joe": "M", "Johan-Benjamin": "M",
    "Johanna-Maria": "K", "Jonatan": "M", "Jorn-Dieter": "M", "Joseph": "M", "Joshua": "M",
    "Juan": "M", "Judithe": "K", "Julien": "M", "Juliette": "K", "Kalbiye": "K",
    "Kamila": "K", "Karen-Margrethe": "K", "Karl-Henrik": "M", "Karl-Åge": "M", "Kaspar": "M",
    "Kasper-Peder": "M", "Kassandra": "K", "Katie": "K", "Keen": "M", "Kenni": "M",
    "Keren": "M", "Kevin": "M", "Khadija": "K", "Khalid": "M", "Kifaax": "M",
    "Kira": "K", "Kirsten-Marie": "K", "Kirstina": "K", "Kitna": "K", "Krestian": "M",
    "Kris": "M", "Kristjar": "M", "Kristopher": "M", "Kæthe": "K", "Lars-Christian": "M",
    "Lars-Emil": "M", "Lars-Peter": "M", "Lartey": "M", "Larysa": "K", "Laus": "M",
    "Laust": "M", "Lave": "M", "Leise": "K", "Lene-Theresa": "K", "Lennie": "K",
    "Lesia": "K", "Lindhardt": "M", "Lise-Lotte": "K", "Liseliva": "K", "Lismirah": "K",
    "Liva": "K", "Lola": "K", "Lolan": "K", "Lorena": "K", "Louie": "M",
    "Lubima": "K", "Lucas": "M", "Lucca": "K", "Lucia": "K", "Lukas": "M",
    "Lukasz": "M", "Luna": "K", "Lærke": "K", "Mads-Emil": "M", "Mads-Magnus": "M",
    "Mads-Peder": "M", "Mai-Britt": "K", "Maia": "K", "Maikhen": "K", "Maj-Britt": "K",
    "Malde": "M", "Malena": "K", "Malgorzata": "K", "Malika": "K", "Malou": "K",
    "Malthe": "M", "Malue": "K", "Manuel": "M", "Manuela": "K", "Marc": "M",
    "Marcel": "M", "Marck": "M", "Marco": "M", "Maria-Irina": "K", "Mariane": "K",
    "Marie-Louise": "K", "Mariola": "K", "Marion": "K", "Marthin": "M", "Marthine": "M",
    "Mary-Ann": "K", "Matheus": "M", "Mathilda": "K", "Matilde": "K", "Matthew": "M",
    "May-Britt": "K", "Maya": "K", "Maya-Louise": "K", "Medhat": "M", "Mehmet": "M",
    "Meiner": "M", "Melina": "K", "Melissa": "K", "Meran": "M", "Methe": "K",
    "Mette-Emilie": "K", "Mette-Marie": "K", "Mette-Rose": "K", "Miasser": "K", "Michaeel": "M",
    "Michael-Tem": "M", "Michaell": "M", "Mika": "K", "Mike": "M", "Miklas": "M",
    "Milishia": "K", "Mina": "K", "Mirela": "K", "Misja": "K", "Mitra": "K",
    "Mohamad": "M", "Mohamed": "M", "Mohammad": "M", "Mohammadreza": "M", "Mohamud": "M",
    "Mohat": "M", "Morgan": "M", "Mostafa": "K", "Muhamed": "M", "Muhammad": "M",
    "Muj": "M", "Murat": "M", "Musa": "M", "Mussa": "K", "Mustafa": "M",
    "Mustapha": "K", "Muuse": "M", "Muzafar": "M", "Nadja": "K", "Nageib": "M",
    "Naja-Kathrine": "K", "Nangiyalay": "M", "Natalia": "K", "Natascha": "K", "Natasha": "K",
    "Natasja": "K", "Natassia": "K", "Nathasja": "K", "Natja": "K", "Necla": "K",
    "Nelle": "K", "Nellie": "K", "Nermina": "K", "Nichlas": "M", "Nicholai": "M",
    "Nicholas": "M", "Nick": "M", "Nickolai": "M", "Nico": "M", "Nicola": "K",
    "Nicolas": "M", "Niels-Christian": "M", "Niels-Erik": "M", "Niels-Jørgen": "M", "Niels-Ole": "M",
    "Niels-Peter": "M", "Niki": "M", "Nikoline": "K", "Nilas": "M", "Nils-Erik": "M",
    "Nitasha": "K", "Njord": "M", "Noah": "M", "Nohr": "M", "Noor": "M",
    "Nordin": "M", "Oguzcan": "M", "Oksana": "K", "Oleksandr": "M", "Olena": "M",
    "Olfert": "M", "Olivia": "K", "Omar": "M", "Osama": "K", "Ozkan": "M",
    "Padideh": "K", "Paskar": "M", "Patrizia": "K", "Pax": "M", "Pernelle": "M",
    "Peshtiwan": "M", "Petrus": "M", "Pierre": "M", "Piratheep": "M", "Polly-Nicole": "K",
    "Poul-Erik": "M", "Poul-Henrik": "M", "Purnima": "K", "Pylle": "K", "Qasam": "M",
    "Rafael-Raducu": "M", "Raged": "M", "Ragnar-Gwyn": "M", "Ragner": "M", "Rainer": "M",
    "Rajinder": "M", "Rameesh": "M", "Rashid": "M", "Raul-Ionel": "M", "Regina": "K",
    "Regine": "K", "Regitse": "K", "Rejin": "K", "Renette": "M", "Renè": "M",
    "Riber": "M", "Ric": "M", "Rico": "M", "Roman": "M", "Romante": "K",
    "Romeo": "M", "Rosalina": "K", "Rose-Marie": "K", "Roya": "K", "Rudy": "M",
    "Rukhsana": "K", "Rumle": "M", "Sabina": "K", "Sabrina": "K", "Said": "M",
    "Salah": "K", "Saliem": "M", "Salik": "M", "Samagarny": "M", "Samira": "K",
    "Samsam": "M", "Samuel": "M", "Sanna": "K", "Santana": "K", "Santhalogini": "K",
    "Sarfraz": "M", "Sascha": "K", "Sedi": "K", "Sejr": "M", "Selcuk": "M",
    "Selina": "K", "Serdar": "M", "Serena": "K", "Shawn": "M", "Sheldon": "M",
    "Shemon": "M", "Sie": "K", "Signe-Elisabeth": "K", "Sikandar": "M", "Silas": "M",
    "Sinisa": "K", "Siobhán": "K", "Smilla": "K", "Smita": "K", "Soma": "K",
    "Sophia": "K", "Soraya": "K", "Stanley": "M", "Steen-Ove": "M", "Stephanie": "K",
    "Stephen": "M", "Steven": "M", "Stinne": "K", "Stinus": "M", "Summer": "K",
    "Sussy": "K", "Suzette": "K", "Svend-Aage": "M", "Svend-Erik": "M", "Svenn-Erik": "M",
    "Svenning": "M", "Svitlana": "K", "Syed": "M", "Syeda": "M", "Sytter": "M",
    "Søsser": "K", "Taner": "M", "Tania": "K", "Tasia": "K", "Taya": "K",
    "Tetiana": "K", "Thake": "M", "Tharsika": "K", "Thea": "K", "Thekla": "K",
    "Theodore": "M", "Theresa": "K", "Thies": "M", "Thrine": "K", "Thue": "M",
    "Thøger": "M", "Tina-Mia": "K", "Tinna": "K", "Tola": "K", "Tormod": "M",
    "Tristan": "M", "Ulrikka": "K", "Unnie": "K", "Vanja": "K", "Viktoria": "K",
    "Villads": "M", "Villum": "M", "Vincent": "M", "Vittus": "M", "Vladimir": "M",
    "Volker": "M", "Wanda": "K", "Waqar": "M", "Wickie": "K", "Yasmin": "K",
    "Yasser": "M", "Zahra": "K", "Zaklina": "K", "Zeb": "M", "Zeljka": "K",
    "Zena": "K", "Zeynep": "K", "Zishan": "M", "Zitta": "K", "Åsbjørn": "M",
    "Øzgen": "M",
}

def estimér_køn(fornavn):
    """
    Estimerer køn baseret på fornavn.
    Returnerer tuple: (køn, metode)
    - køn: 'M', 'K', eller 'Ukendt'
    - metode: 'manuel identifikation', 'AI-vurdering', eller 'gender-guesser'

    Prioritering:
    1. Manuel database (1151 manuelt + AI identificerede navne)
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
    if clean_name in MANUEL_KØNSBESTEMMELSE:
        return MANUEL_KØNSBESTEMMELSE[clean_name], 'manuel identifikation'

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

def fladgør_kandidatdata_kvrv(json_data):
    """
    Fladgør kandidatdata for kommunal/regionsrådsvalg.
    Returnerer liste af kandidater med alle relevante felter.
    Håndterer både gammel og ny JSON-struktur fra valg.dk.
    """
    kandidater = []

    # Tjek om det er den nye struktur (direkte felter) eller gammel (nested under "Valg")
    if "Valgart" in json_data:
        # NY STRUKTUR fra valg.dk 2025

        # Skip data fra tidligere valg (kun 2025 data)
        valgdag = json_data.get("Valgdag", "")
        if valgdag and "-2025" not in valgdag:
            return []  # Spring over data fra tidligere valg

        valg_info = {
            "ValgId": json_data.get("KommuneDagiId") or json_data.get("RegionDagiId", ""),
            "ValgNavn": json_data.get("Valgart", ""),
            "ValgDato": valgdag,
            "KommuneKode": json_data.get("KommuneDagiId", ""),
            "KommuneNavn": json_data.get("Kommune", ""),
            "RegionKode": json_data.get("RegionDagiId", ""),
            "RegionNavn": json_data.get("Region", ""),
            "FrigivelsesTidspunkt": json_data.get("FrigivelsesTidspunktUTC", ""),
            "OpdateringsTidspunkt": json_data.get("OpdateringsTidspunktUTC", ""),
        }

        kandidatlister = json_data.get("Kandidatlister", [])

        for liste in kandidatlister:
            liste_info = {
                "ListeBogstav": liste.get("Bogstavbetegnelse", ""),
                "ListeNavn": liste.get("Navn", ""),
                "ListeId": liste.get("KandidatlisteId", ""),
                "Stemmeseddelplacering": liste.get("Stemmeseddelsplacering", ""),
                "Opstillingsform": liste.get("Opstillingsform", ""),
            }

            for kandidat in liste.get("Kandidater", []):
                # Navn kan være helt navn eller opdelt
                navn = kandidat.get("Navn", "")
                stemmeseddelnavn = kandidat.get("Stemmeseddelnavn", navn)

                if " " in navn:
                    dele = navn.split(" ", 1)
                    fornavn = dele[0]
                    efternavn = dele[1] if len(dele) > 1 else ""
                else:
                    fornavn = navn
                    efternavn = ""

                # Estimér køn
                estimeret_køn, køns_metode = estimér_køn(fornavn)

                row = {
                    **valg_info,
                    **liste_info,
                    "KandidatId": kandidat.get("Id", ""),
                    "Navn": navn,
                    "Stemmeseddelnavn": stemmeseddelnavn,
                    "Fornavn": fornavn,
                    "Efternavn": efternavn,
                    "EstimeretKøn": estimeret_køn,
                    "KønsMetode": køns_metode,
                    "Stilling": kandidat.get("Stilling", ""),
                    "Bopæl": kandidat.get("BopaelPaaStemmeseddel", ""),
                    "KandidatPlacering": kandidat.get("Stemmeseddelsplacering", ""),
                }
                kandidater.append(row)
    else:
        # GAMMEL STRUKTUR (fallback)
        valg = json_data.get("Valg", json_data)
        valg_info = {
            "ValgId": valg.get("Id", ""),
            "ValgNavn": valg.get("Navn", ""),
            "ValgDato": valg.get("Dato", ""),
            "KommuneKode": valg.get("KommuneReference", {}).get("Kode", ""),
            "KommuneNavn": valg.get("KommuneReference", {}).get("Navn", ""),
            "RegionKode": valg.get("RegionReference", {}).get("Kode", ""),
            "RegionNavn": valg.get("RegionReference", {}).get("Navn", ""),
        }

        kandidatlister = valg.get("Kandidatlister", [])

        for liste in kandidatlister:
            liste_info = {
                "ListeBogstav": liste.get("Bogstav", ""),
                "ListeNavn": liste.get("Navn", ""),
                "ListeId": liste.get("Id", ""),
                "Stemmeseddelplacering": liste.get("Stemmeseddelplacering", ""),
            }

            for kandidat in liste.get("Kandidater", []):
                fornavn = kandidat.get("Fornavn", "")

                # Estimér køn
                estimeret_køn, køns_metode = estimér_køn(fornavn)

                row = {
                    **valg_info,
                    **liste_info,
                    "KandidatId": kandidat.get("Id", ""),
                    "Fornavn": fornavn,
                    "Efternavn": kandidat.get("Efternavn", ""),
                    "EstimeretKøn": estimeret_køn,
                    "KønsMetode": køns_metode,
                    "Stilling": kandidat.get("Stilling", ""),
                    "Bopæl": kandidat.get("Bopæl", ""),
                    "KandidatPlacering": kandidat.get("Placering", ""),
                }
                kandidater.append(row)

    return kandidater


def fladgør_valgresultater_kvrv(json_data):
    """
    Fladgør valgresultater for kommunal/regionsrådsvalg.
    Returnerer liste af resultater på kandidat-niveau.
    """
    resultater = []

    # Håndter både ny struktur (direkte felter) og gammel (nested under "Valgresultater")
    if "Valgart" in json_data:
        # NY STRUKTUR 2025
        # Skip data fra tidligere valg (kun 2025 data)
        valgdag = json_data.get("Valgdag", "")
        if valgdag and "-2025" not in valgdag:
            return []  # Spring over data fra tidligere valg

        valg = json_data
    else:
        valg = json_data.get("Valgresultater", json_data)

    # Grundlæggende info om afstemningsområdet
    stemmeberettigede = valg.get("AntalStemmeberettigedeVælgere", valg.get("Stemmeberettigede", 0))
    afgivne_stemmer = valg.get("AfgivneStemmer", 0)
    gyldige_stemmer = valg.get("GyldigeStemmer", 0)
    ugyldige_stemmer = valg.get("UgyldigeStemmerUdoverBlanke", valg.get("UgyldigeStemmer", 0))
    blanke_stemmer = (valg.get("BlankeUgyldigeFremmødteStemmer", 0) +
                     valg.get("BlankeUgyldigeBrevstemmer", 0)) or valg.get("BlankeStemmer", 0)

    # Beregn valgdeltagelse
    valgdeltagelse_pct = (afgivne_stemmer / stemmeberettigede * 100) if stemmeberettigede > 0 else 0
    gyldige_pct = (gyldige_stemmer / afgivne_stemmer * 100) if afgivne_stemmer > 0 else 0

    valg_info = {
        "Valgart": valg.get("Valgart", valg.get("ValgNavn", "")),
        "Valgdag": valg.get("Valgdag", valg.get("ValgDato", "")),
        "AfstemningsområdeDagiId": valg.get("AfstemningsområdeDagiId", ""),
        "AfstemningsområdeNummer": valg.get("AfstemningsområdeNummer", valg.get("AfstemningsområdeReference", {}).get("Nummer", "")),
        "Afstemningsområde": valg.get("Afstemningsområde", valg.get("AfstemningsområdeReference", {}).get("Navn", "")),
        "Kommune": valg.get("Kommune", valg.get("KommuneReference", {}).get("Navn", "")),
        "Kommunekode": valg.get("Kommunekode", valg.get("KommuneReference", {}).get("Kode", "")),
        "Stemmeberettigede": stemmeberettigede,
        "AfgivneStemmer": afgivne_stemmer,
        "GyldigeStemmer": gyldige_stemmer,
        "UgyldigeStemmer": ugyldige_stemmer,
        "BlankeStemmer": blanke_stemmer,
        "ValgdeltagelseProcent": round(valgdeltagelse_pct, 2),
        "GyldigeProcent": round(gyldige_pct, 2),
        "Resultatart": valg.get("Resultatart", ""),
        "GodkendelsesDato": valg.get("GodkendelsesDatoUTC", ""),
        "FrigivelsesTidspunkt": valg.get("FrigivelsesTidspunktUTC", ""),
        "AfgivneStemmerÆndring": valg.get("AfgivneStemmerDifferenceFraForrigeValg", ""),
        "GyldigeStemmerÆndring": valg.get("GyldigeStemmerDifferenceFraForrigeValg", ""),
        "StemmeberettigedeÆndring": valg.get("AntalStemmeberettigedeVælgereDifferenceFraForrigeValg", ""),
    }

    # Hent kandidatlister med stemmer
    for liste in valg.get("Kandidatlister", []):
        liste_stemmer = liste.get("Stemmer", 0)
        stemmer_ændring = liste.get("StemmerDifferenceFraForrigeValg", "")

        liste_info = {
            "ListeBogstav": liste.get("Bogstavbetegnelse", liste.get("Bogstav", "")),
            "ListeNavn": liste.get("Navn", ""),
            "ListeId": liste.get("KandidatlisteId", liste.get("Id", "")),
            "ListeStemmer": liste_stemmer,
            "ListeStemmerÆndring": stemmer_ændring,
            "Listestemmer": liste.get("Listestemmer", 0),
        }

        # Hent kandidater med personlige stemmer
        for kandidat in liste.get("Kandidater", []):
            personlige_stemmer = kandidat.get("Stemmer", kandidat.get("PersonligeStemmer", 0))

            # Beregn personlig stemmeandel
            personlig_andel_pct = (personlige_stemmer / liste_stemmer * 100) if liste_stemmer > 0 else 0

            row = {
                **valg_info,
                **liste_info,
                "KandidatId": kandidat.get("Id", ""),
                "Stemmeseddelnavn": kandidat.get("Stemmeseddelnavn", ""),
                "PersonligeStemmer": personlige_stemmer,
                "PersonligStemmeAndelProcent": round(personlig_andel_pct, 2),
            }
            resultater.append(row)

    return resultater


def fladgør_mandatfordeling(json_data):
    """
    Fladgør mandatfordeling for kommunal/regionsrådsvalg.
    Inkluderer både valgte kandidater og stedfortrædere.
    """
    mandater = []

    # Håndter både ny og gammel struktur
    if "Valgart" in json_data:
        # NY STRUKTUR 2025
        # Skip data fra tidligere valg (kun 2025 data)
        valgdag = json_data.get("Valgdag", "")
        if valgdag and "-2025" not in valgdag:
            return []  # Spring over data fra tidligere valg

        valg_info = {
            "Valgart": json_data.get("Valgart", ""),
            "Valgdag": valgdag,
            "KommuneKode": json_data.get("Kommunekode", ""),
            "Kommune": json_data.get("Kommune", ""),
            "Resultatart": json_data.get("Resultatart", ""),
            "FrigivelsesTidspunkt": json_data.get("FrigivelsesTidspunktUTC", ""),
        }
    else:
        valg = json_data.get("Valg", json_data)
        valg_info = {
            "ValgId": valg.get("Id", ""),
            "KommuneKode": valg.get("KommuneReference", {}).get("Kode", ""),
            "Kommune": valg.get("KommuneReference", {}).get("Navn", ""),
        }

    # Personlige mandater
    for mandat in json_data.get("PersonligeMandater", []):
        # Ny struktur
        if "KandidatId" in mandat:
            row = {
                **valg_info,
                "MandatType": "Personligt",
                "MandatNummer": mandat.get("Nummer", mandat.get("MandatNummer", "")),
                "NummerAnførtPåListen": mandat.get("NummerAnførtPåListen", ""),
                "KandidatId": mandat.get("KandidatId", ""),
                "Stemmeseddelnavn": mandat.get("Stemmeseddelnavn", ""),
                "ListeId": mandat.get("KandidatlisteId", ""),
                "ListeNavn": mandat.get("KandidatlisteNavn", ""),
                "ListeBogstav": mandat.get("Bogstavbetegnelse", ""),
            }
        else:
            # Gammel struktur
            row = {
                **valg_info,
                "MandatType": "Personligt",
                "MandatNummer": mandat.get("MandatNummer", ""),
                "KandidatId": mandat.get("KandidatReference", {}).get("Id", ""),
                "Fornavn": mandat.get("KandidatReference", {}).get("Fornavn", ""),
                "Efternavn": mandat.get("KandidatReference", {}).get("Efternavn", ""),
            }
        mandater.append(row)

    # Listemandater
    for mandat in json_data.get("ListeMandater", []):
        # Ny struktur
        if "KandidatlisteId" in mandat or "Bogstavbetegnelse" in mandat:
            row = {
                **valg_info,
                "MandatType": "Liste",
                "MandatNummer": mandat.get("Nummer", mandat.get("MandatNummer", "")),
                "ListeId": mandat.get("KandidatlisteId", ""),
                "ListeBogstav": mandat.get("Bogstavbetegnelse", ""),
                "ListeNavn": mandat.get("KandidatlisteNavn", ""),
            }
        else:
            # Gammel struktur
            row = {
                **valg_info,
                "MandatType": "Liste",
                "MandatNummer": mandat.get("MandatNummer", ""),
                "ListeId": mandat.get("KandidatlisteReference", {}).get("Id", ""),
                "ListeBogstav": mandat.get("KandidatlisteReference", {}).get("Bogstav", ""),
                "ListeNavn": mandat.get("KandidatlisteReference", {}).get("Navn", ""),
            }
        mandater.append(row)

    # Stedfortrædere (suppleanter) - kun i ny struktur
    for kandidatliste in json_data.get("Kandidatliste", []):
        liste_info = {
            "ListeId": kandidatliste.get("KandidatlisteId", ""),
            "ListeNavn": kandidatliste.get("KandidatlisteNavn", ""),
            "ListeBogstav": kandidatliste.get("Bogstavbetegnelse", ""),
        }

        for stedfortræder in kandidatliste.get("Stedfortrædere", []):
            row = {
                **valg_info,
                **liste_info,
                "MandatType": "Stedfortræder",
                "StedfortræderNummer": stedfortræder.get("Nummer", ""),
                "KandidatId": stedfortræder.get("KandidatId", ""),
                "Stemmeseddelnavn": stedfortræder.get("Stemmeseddelnavn", ""),
            }
            mandater.append(row)

    return mandater


def process_json_files(json_mappe, output_mappe):
    """
    Hovedfunktion: Læser alle JSON-filer og konverterer til Excel.
    """
    json_mappe = Path(json_mappe)
    output_mappe = Path(output_mappe)
    output_mappe.mkdir(exist_ok=True)

    # Saml data i kategorier - både samlet og opdelt
    alle_kandidater = []
    alle_resultater = []
    alle_mandater = []

    kommunal_kandidater = []
    kommunal_resultater = []
    kommunal_mandater = []

    regions_kandidater = []
    regions_resultater = []
    regions_mandater = []

    # Find alle JSON-filer
    json_filer = list(json_mappe.rglob("*.json"))
    print(f"Fundet {len(json_filer)} JSON-filer i {json_mappe}")

    if not json_filer:
        print("ADVARSEL: Ingen JSON-filer fundet!")
        return
    
    for json_fil in json_filer:
        # Spring over verifikationsdata (testdata fra KOMBIT)
        if 'verifikation' in str(json_fil):
            print(f"Springer over verifikationsdata: {json_fil.name}")
            continue

        print(f"Behandler: {json_fil.name}")

        try:
            # Læs JSON med UTF-8 encoding og håndter BOM
            with open(json_fil, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
            
            filnavn = json_fil.name.lower()
            
            # Kategoriser og fladgør baseret på filtype
            er_kommunal = "kommunalvalg" in filnavn
            er_regions = "regionsrådsvalg" in filnavn or "region" in filnavn

            if "kandidat-data" in filnavn:
                if "kommunalvalg" in filnavn or "regionsrådsvalg" in filnavn:
                    kandidater = fladgør_kandidatdata_kvrv(data)
                    alle_kandidater.extend(kandidater)

                    if er_kommunal:
                        kommunal_kandidater.extend(kandidater)
                    if er_regions:
                        regions_kandidater.extend(kandidater)

                    print(f"  → {len(kandidater)} kandidater")

            elif "valgresultater" in filnavn:
                if "kommunalvalg" in filnavn or "regionsrådsvalg" in filnavn or "kvrv" in filnavn.lower():
                    resultater = fladgør_valgresultater_kvrv(data)
                    alle_resultater.extend(resultater)

                    if er_kommunal:
                        kommunal_resultater.extend(resultater)
                    if er_regions:
                        regions_resultater.extend(resultater)

                    print(f"  → {len(resultater)} resultatrækker")

            elif "mandatfordeling" in filnavn:
                mandater = fladgør_mandatfordeling(data)
                alle_mandater.extend(mandater)

                if er_kommunal:
                    kommunal_mandater.extend(mandater)
                if er_regions:
                    regions_mandater.extend(mandater)

                print(f"  → {len(mandater)} mandater")
            
            else:
                # Generisk håndtering - prøv at flade JSON ud
                if isinstance(data, list):
                    df = pd.json_normalize(data)
                else:
                    df = pd.json_normalize([data])
                
                output_fil = output_mappe / f"{json_fil.stem}.xlsx"
                df.to_excel(output_fil, index=False)
                print(f"  → Gemt som {output_fil.name}")
        
        except json.JSONDecodeError as e:
            print(f"  ✗ JSON-fejl: {e}")
        except Exception as e:
            print(f"  ✗ Fejl: {e}")
    
    # Gem samlede data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    print("\n" + "=" * 60)
    print("GEMMER EXCEL-FILER")
    print("=" * 60)

    # SAMLEDE FILER (kommunal + regional)
    if alle_kandidater:
        df = pd.DataFrame(alle_kandidater)
        output_fil = output_mappe / f"kandidater_ALLE_VALG_{timestamp}.xlsx"
        df.to_excel(output_fil, index=False, engine='openpyxl')
        print(f"\n✓ Alle kandidater gemt: {output_fil.name}")
        print(f"  {len(alle_kandidater)} rækker, {len(df.columns)} kolonner")

    if alle_resultater:
        df = pd.DataFrame(alle_resultater)
        output_fil = output_mappe / f"valgresultater_ALLE_VALG_{timestamp}.xlsx"
        df.to_excel(output_fil, index=False, engine='openpyxl')
        print(f"\n✓ Alle valgresultater gemt: {output_fil.name}")
        print(f"  {len(alle_resultater)} rækker, {len(df.columns)} kolonner")

        # Lav også en pivottabel med resultater pr. kommune/region
        if 'Kommune' in df.columns and 'ListeNavn' in df.columns:
            pivot = df.groupby(['Kommune', 'ListeNavn'])['PersonligeStemmer'].sum().reset_index()
            pivot_fil = output_mappe / f"resultater_per_kommune_region_{timestamp}.xlsx"
            pivot.to_excel(pivot_fil, index=False, engine='openpyxl')
            print(f"✓ Pivottabel gemt: {pivot_fil.name}")

    if alle_mandater:
        df = pd.DataFrame(alle_mandater)
        output_fil = output_mappe / f"mandatfordeling_ALLE_VALG_{timestamp}.xlsx"
        df.to_excel(output_fil, index=False, engine='openpyxl')
        print(f"\n✓ Alle mandater gemt: {output_fil.name}")
        print(f"  {len(alle_mandater)} rækker")

    # SEPARATE FILER FOR KOMMUNALVALG
    print("\n" + "-" * 60)
    print("KOMMUNALVALG")
    print("-" * 60)

    if kommunal_kandidater:
        df = pd.DataFrame(kommunal_kandidater)
        output_fil = output_mappe / f"kandidater_KOMMUNAL_{timestamp}.xlsx"
        df.to_excel(output_fil, index=False, engine='openpyxl')
        print(f"✓ Kommunale kandidater: {output_fil.name}")
        print(f"  {len(kommunal_kandidater)} rækker, {len(df.columns)} kolonner")

    if kommunal_resultater:
        df = pd.DataFrame(kommunal_resultater)
        output_fil = output_mappe / f"valgresultater_KOMMUNAL_{timestamp}.xlsx"
        df.to_excel(output_fil, index=False, engine='openpyxl')
        print(f"✓ Kommunale resultater: {output_fil.name}")
        print(f"  {len(kommunal_resultater)} rækker, {len(df.columns)} kolonner")

    if kommunal_mandater:
        df = pd.DataFrame(kommunal_mandater)
        output_fil = output_mappe / f"mandatfordeling_KOMMUNAL_{timestamp}.xlsx"
        df.to_excel(output_fil, index=False, engine='openpyxl')
        print(f"✓ Kommunale mandater: {output_fil.name}")
        print(f"  {len(kommunal_mandater)} rækker")

    # SEPARATE FILER FOR REGIONSRÅDSVALG
    print("\n" + "-" * 60)
    print("REGIONSRÅDSVALG")
    print("-" * 60)

    if regions_kandidater:
        df = pd.DataFrame(regions_kandidater)
        output_fil = output_mappe / f"kandidater_REGIONAL_{timestamp}.xlsx"
        df.to_excel(output_fil, index=False, engine='openpyxl')
        print(f"✓ Regionale kandidater: {output_fil.name}")
        print(f"  {len(regions_kandidater)} rækker, {len(df.columns)} kolonner")

    if regions_resultater:
        df = pd.DataFrame(regions_resultater)
        output_fil = output_mappe / f"valgresultater_REGIONAL_{timestamp}.xlsx"
        df.to_excel(output_fil, index=False, engine='openpyxl')
        print(f"✓ Regionale resultater: {output_fil.name}")
        print(f"  {len(regions_resultater)} rækker, {len(df.columns)} kolonner")

    if regions_mandater:
        df = pd.DataFrame(regions_mandater)
        output_fil = output_mappe / f"mandatfordeling_REGIONAL_{timestamp}.xlsx"
        df.to_excel(output_fil, index=False, engine='openpyxl')
        print(f"✓ Regionale mandater: {output_fil.name}")
        print(f"  {len(regions_mandater)} rækker")

    print("\n" + "=" * 60)
    print(f"✅ KONVERTERING FÆRDIG!")
    print(f"📁 Se alle filer i: {output_mappe}")
    print("=" * 60)


def main():
    if len(sys.argv) < 2:
        print("Brug: python valg_json_til_excel.py <json_mappe> [output_mappe]")
        print("\nEksempel:")
        print('  python valg_json_til_excel.py "C:\\Users\\Nils\\valg_data" "C:\\Users\\Nils\\excel_output"')
        sys.exit(1)
    
    json_mappe = sys.argv[1]
    output_mappe = sys.argv[2] if len(sys.argv) > 2 else Path(json_mappe) / "excel_output"
    
    print("=" * 60)
    print("VALG.DK JSON til Excel Konvertering")
    print("=" * 60)
    print(f"JSON-mappe: {json_mappe}")
    print(f"Output-mappe: {output_mappe}")
    print()
    
    process_json_files(json_mappe, output_mappe)


if __name__ == "__main__":
    main()
