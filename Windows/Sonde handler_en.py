#-------------------------------------------------------------------------------
# Name:        Sonde handler
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
from datetime import datetime


# Load config.ini
config = configparser.ConfigParser()
config.read('config.ini')

# Load data from config.ini
sender_email = config.get('settings', 'sender_email')
receiver_email = config.get('settings', 'receiver_email')
app_password = config.get('settings', 'app_password')
home_latitude = float(config.get('settings', 'home_latitude'))
home_longitude = float(config.get('settings', 'home_longitude'))
distance_from_home = float(config.get('settings', 'distance_from_home'))
interval = int(config.get('settings', 'interval'))

# Path to file of data if sent email for sonde before
sent_sondes_file = 'sent_sondes.txt'

# Haversine function for calculate betwen two position
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # radius of the earth in km

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance

# Function for send e-mail
def send_email(sonde_id, typ, date_time, latitude, longitude, course, speed, altitude, climb, launch, frequency, distance):
    subject = f"Sonde {sonde_id} in radius {distance:.2f} km from Home position"
    body = (f"Sonde ID: {sonde_id}\n"
            f"Typ: {typ}\n"
            f"Date and Time: {date_time}\n"
            f"Latitude: {latitude}\n"
            f"Longitude: {longitude}\n"
            f"Course: {course}\n"
            f"Speed: {speed}\n"
            f"Altitude: {altitude}\n"
            f"Climb: {climb}\n"
            f"Launch city: {launch}\n"
            f"Frequency: {frequency}\n"
            f"Distance from Home location: {distance:.2f} km\n")

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = receiver_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        print(f"E-mail sent for {sonde_id}*********************************************")
        # Save ID sonde if e-mail was sendt
        with open(sent_sondes_file, 'a') as file:
            file.write(sonde_id + '\n')
    except Exception as e:
        print(f"Error during send e-maila: {e} ?????????????????????????????????")

# Function if e-mail was sent for current sonde
def email_sent(sonde_id):
    try:
        with open(sent_sondes_file, 'r') as file:
            sent_sondes = file.read().splitlines()
        return sonde_id in sent_sondes
    except FileNotFoundError:
        return False

# Function for load data from Radiosondy.info and send e-mail
def process_data():
    url = r'https://radiosondy.info/dyn/get_flying.php'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = pd.read_html(response.content)[0].values.tolist()
    else:
        print(f"Error {response.status_code}: Error loading web Radiosondy.info")
        return

    # Ekstract data for each one sonde and calculate distance from Home position
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

        # Calculate distance

        distance = haversine(home_latitude, home_longitude, latitude, longitude)
        print(f"Distance {sonde_id} from Home location: {distance:.2f} km")

        # If distance is lower then set and not send e-mail before, sent e-mail now
        if distance < distance_from_home and not email_sent(sonde_id):
            send_email(sonde_id, typ, date_time, latitude, longitude, course, speed, altitude, climb, launch, frequency, distance)

# Set interval for reload Radiosondy.info in seconds
try:
    while True:
        # get time now
        dt = datetime.now()
        # format it to a string
        timeStamp = dt.strftime('%Y-%m-%d %H:%M:%S')

        # print it to screen
        # print(timeStamp)
        process_data()
        print(f"{timeStamp} -- Waiting {interval} second before reload data from Radiosondy.info... CTRL + C for EXIT!")
        time.sleep(interval)
except KeyboardInterrupt:
    print("Program is treminated!!.")
    sys.exit()
