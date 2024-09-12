#-------------------------------------------------------------------------------
# Name:        Sonde handler za Linux
# Purpose:
#
# Author:      9A4AM
#
# Created:     12.09.2024
# Copyright:   (c) 9A4AM 2024
# Licence:     <your licence>
#-------------------------------------------------------------------------------
import pandas as pd
import requests
from math import radians, sin, cos, sqrt, atan2
import smtplib
from email.mime.text import MIMEText
import time
import configparser
import sys
import os
from datetime import datetime

# Učitavanje konfiguracije iz config.ini (koristimo apsolutnu putanju)
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))

# Učitavanje varijabli iz konfiguracije
sender_email = config.get('settings', 'sender_email')
receiver_email = config.get('settings', 'receiver_email')
app_password = config.get('settings', 'app_password')
home_latitude = float(config.get('settings', 'home_latitude'))
home_longitude = float(config.get('settings', 'home_longitude'))
distance_from_home = float(config.get('settings', 'distance_from_home'))
interval = int(config.get('settings', 'interval'))

# Putanja do datoteke koja sadrži ID-ove sondi za koje su emailovi poslani (koristimo apsolutnu putanju)
sent_sondes_file = os.path.join(os.path.dirname(__file__), 'sent_sondes.txt')

# Haversine funkcija za izračunavanje udaljenosti između dvije točke
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Polumjer Zemlje u kilometrima

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance

# Funkcija za slanje emaila
def send_email(sonde_id, typ, date_time, latitude, longitude, course, speed, altitude, climb, launch, frequency, distance):
    subject = f"Sonda {sonde_id} je u radijusu {distance} od vas"
    body = (f"Sonde ID: {sonde_id}\n"
            f"Tip: {typ}\n"
            f"Datum i vrijeme: {date_time}\n"
            f"Latitude: {latitude}\n"
            f"Longitude: {longitude}\n"
            f"Kurs: {course}\n"
            f"Brzina: {speed}\n"
            f"Visina: {altitude}\n"
            f"Brzina penjanja: {climb}\n"
            f"Lokacija lansiranja: {launch}\n"
            f"Frekvencija: {frequency}\n"
            f"Udaljenost od Home lokacije: {distance:.2f} km\n")

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = receiver_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        print(f"Email je poslan za sondu {sonde_id} *****************************************")
        # Zabilježi ID sonde za koju je poslat email
        with open(sent_sondes_file, 'a') as file:
            file.write(sonde_id + '\n')
    except Exception as e:
        print(f"Došlo je do greške prilikom slanja emaila: {e} #####################################")

# Funkcija za proveru da li je email već poslan za određenu sondu
def email_sent(sonde_id):
    try:
        with open(sent_sondes_file, 'r') as file:
            sent_sondes = file.read().splitlines()
        return sonde_id in sent_sondes
    except FileNotFoundError:
        return False

# Funkcija za učitavanje podataka i slanje emaila
def process_data():
    url = r'https://radiosondy.info/dyn/get_flying.php'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = pd.read_html(response.content)[0].values.tolist()
    else:
        print(f"Greška {response.status_code}: Nije moguće učitati stranicu")
        return

    # Ekstrakcija podataka za svaki objekat i izračunavanje udaljenosti
    for row in data:
        sonde_id = row[0]
        typ = row[1]
        date_time = row[2]
        latitude = row[3]
        longitude = row[4]
        course = row[5]
        speed = row[6]
        altitude = row[7]
        climb = row[8]
        launch = row[9]
        frequency = row[10]

        # Izračunavanje udaljenosti
        distance = haversine(home_latitude, home_longitude, latitude, longitude)
        print(f"Udaljenost od Home lokacije: {distance:.2f} km")

        # Ako je udaljenost manja od zadane udaljenosti i email još nije poslan za ovu sondu, šaljem email
        if distance < distance_from_home and not email_sent(sonde_id):
            send_email(sonde_id, typ, date_time, latitude, longitude, course, speed, altitude, climb, launch, frequency, distance)

# Postavi interval za učitavanje stranice u sekundama
try:
    while True:
        # Učitaj vrijeme sada
        dt = datetime.now()
        # formiraj string
        timeStamp = dt.strftime('%Y-%m-%d %H:%M:%S')

        # Ispiši na zaslon
        # print(timeStamp)
        process_data()
        print(f"{timeStamp} -- Čekam {interval} sekundi prije ponovnog učitavanja... CTRL + C za izlaz!")
        time.sleep(interval)
except KeyboardInterrupt:
    print("Program je prekinut.")
    sys.exit()
