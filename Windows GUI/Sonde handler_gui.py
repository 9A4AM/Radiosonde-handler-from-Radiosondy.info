#-------------------------------------------------------------------------------
# Name:        Sonde handler for Windows - GUI version
# Purpose:
#
# Author:      9A4AM
#
# Created:     13.09.2024
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
import tkinter as tk
from tkinter import ttk
from tkinter import font

# GUI Setup
root = tk.Tk()
root.geometry("960x680")
root.title("Sonde Handler from Radiosondy.info by 9A4AM")
root.configure(bg='black')  # Set background color to black

# Define frames
frame1 = tk.Frame(root, bg='black')  # Frame for active sonde display
frame1.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")  # Make it span across two columns

frame2 = tk.Frame(root, bg='black')  # Frame for sent sondes
frame2.grid(row=1, column=0, padx=10, pady=10)

frame3 = tk.Frame(root, bg='black')  # Frame for config display
frame3.grid(row=1, column=1, padx=10, pady=10)

# Display active sondes
tk.Label(frame1, text="LIVE Sonde", font=("Arial", 14), fg='white', bg='black').pack()

tree_sondes = ttk.Treeview(frame1, columns=("ID", "Type", "Date", "Latitude", "Longitude", "Course", "Speed", "Altitude", "Climb", "Launch", "Frequency", "Distance"), show="headings")
tree_sondes.pack()

# Define column headings for active sondes
columns = ["ID", "Type", "Date", "Latitude", "Longitude", "Course", "Speed", "Altitude", "Climb", "Launch", "Frequency", "Distance"]
for col in columns:
    tree_sondes.heading(col, text=col)
    tree_sondes.column(col, width=100, anchor='center')  # Default width, will auto-adjust later

# Function to adjust column widths automatically based on content
def adjust_column_widths(tree):
    for col in columns:
        tree.column(col, width=font.Font().measure(col))
        for row in tree.get_children():
            content = tree.item(row)['values'][columns.index(col)]
            tree.column(col, width=max(tree.column(col, option='width'), font.Font().measure(str(content))))

# Display sent sondes
tk.Label(frame2, text="Sent sonde E-mails", font=("Arial", 14), fg='white', bg='black').pack()

tree_sent_sondes = ttk.Treeview(frame2, columns=("ID"), show="headings")
tree_sent_sondes.pack()

# Define column heading for sent sondes
tree_sent_sondes.heading("ID", text="ID")
tree_sent_sondes.column("ID", width=150, anchor='center')  # Default width, will auto-adjust

# Display settings from config.ini
tk.Label(frame3, text="Settings (config.ini)", font=("Arial", 14), fg='white', bg='black').pack()

config_display = tk.Text(frame3, width=50, height=10, bg='black', fg='white')
config_display.pack()

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
sonde_view_distance = float(config.get('settings', 'sonde_view_distance'))

# Display config.ini data
config_data = (
    f"Sender Email: {sender_email}\n"
    f"Receiver Email: {receiver_email}\n"
    f"Home Latitude: {home_latitude}\n"
    f"Home Longitude: {home_longitude}\n"
    f"Distance from Home: {distance_from_home} km\n"
    f"Interval: {interval} s\n"
    f"Sonde View Distance: {sonde_view_distance} km\n"
)

config_display.insert(tk.END, config_data)
config_display.configure(state='disabled')  # Prevent editing of config display

# Path to file of data if sent email for sonde before
sent_sondes_file = 'sent_sondes.txt'


# Haversine function for calculate between two positions
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # radius of the earth in km

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance

# Function to send e-mail
def send_email(sonde_id, typ, date_time, latitude, longitude, course, speed, altitude, climb, launch, frequency, distance):
    subject = f"Sonde {sonde_id} within {distance:.2f} km from Home position"
    body = (f"Sonde ID: {sonde_id}\n"
            f"Type: {typ}\n"
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
        print(f"Email sent for {sonde_id}")
        with open(sent_sondes_file, 'a') as file:
            file.write(sonde_id + '\n')
    except Exception as e:
        print(f"Error during sending email: {e}")

# Function to check if an email was sent for the current sonde
def email_sent(sonde_id):
    try:
        with open(sent_sondes_file, 'r') as file:
            sent_sondes = file.read().splitlines()
        return sonde_id in sent_sondes
    except FileNotFoundError:
        return False

# Label to display the last update time
last_update_label = tk.Label(root, text="Last update: N/A", font=("Arial", 12), fg='white', bg='black')
last_update_label.grid(row=2, column=0, columnspan=2)

# Function to load data from Radiosondy.info and send email
def process_data():
    url = r'https://radiosondy.info/dyn/get_flying.php'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = pd.read_html(response.content)[0].values.tolist()
    else:
        print(f"Error {response.status_code}: Error loading Radiosondy.info")
        return

    tree_sondes.delete(*tree_sondes.get_children())  # Clear the treeview before inserting new data

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
        print(f"Sonde   {sonde_id : <12} distance from Home location: {distance:.2f} km")

        # Check if the sonde should be displayed
        if distance < sonde_view_distance:
            # Insert data into Treeview
            tree_sondes.insert("", "end", values=(sonde_id, typ, date_time, latitude, longitude, course, speed, altitude, climb, launch, frequency, f"{distance:.2f} km"))

            if distance < distance_from_home and not email_sent(sonde_id):
                send_email(sonde_id, typ, date_time, latitude, longitude, course, speed, altitude, climb, launch, frequency, distance)

    adjust_column_widths(tree_sondes)

    # Update the list of sent sondes
    tree_sent_sondes.delete(*tree_sent_sondes.get_children())  # Clear the treeview
    try:
        with open(sent_sondes_file, 'r') as file:
            sent_sondes = file.read().splitlines()
            for sent_sonde in sent_sondes:
                tree_sent_sondes.insert("", "end", values=(sent_sonde,))
    except FileNotFoundError:
        pass

    # Update last update label with current time
    dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    last_update_label.config(text=f"Last update: {dt}")

# Function to handle periodic updates
def start_processing():
    process_data()
    root.after(interval * 1000, start_processing)



# Exit button
exit_button = tk.Button(root, text="Exit", command=root.quit, bg='red', fg='white', font=("Arial", 12))
exit_button.grid(row=3, column=0, columnspan=2, pady=10)  # Center the button below other frames

# Run the data processing initially and then start the GUI loop
start_processing()
root.mainloop()
