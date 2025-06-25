# Sonde handler for Windows - GUI version (bez pandas)
import requests
from bs4 import BeautifulSoup
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
import socket
import json

# GUI Setup
root = tk.Tk()
root.geometry("1024x720")
root.title("Sonde Handler from Radiosondy.info by 9A4AM")
root.configure(bg='black')

frame1 = tk.Frame(root, bg='black')
frame1.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)

frame1.grid_rowconfigure(0, weight=1)
frame1.grid_columnconfigure(0, weight=1)

frame2 = tk.Frame(root, bg='black')
frame2.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

frame3 = tk.Frame(root, bg='black')
frame3.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

root.grid_rowconfigure(1, weight=1)

tk.Label(frame1, text="LIVE Sonde", font=("Arial", 14), fg='white', bg='black').pack()
columns = ["ID", "Type", "Date", "Latitude", "Longitude", "Course", "Speed", "Altitude", "Climb", "Launch", "Frequency", "Distance"]
tree_sondes = ttk.Treeview(frame1, columns=columns, show="headings")
tree_sondes.pack()
for col in columns:
    tree_sondes.heading(col, text=col)
    tree_sondes.column(col, width=100, anchor='center')

def adjust_column_widths(tree):
    for col in columns:
        tree.column(col, width=font.Font().measure(col))
        for row in tree.get_children():
            content = tree.item(row)['values'][columns.index(col)]
            tree.column(col, width=max(tree.column(col, option='width'), font.Font().measure(str(content))))

tk.Label(frame2, text="Sent sonde E-mails", font=("Arial", 14), fg='white', bg='black').pack()
tree_sent_sondes = ttk.Treeview(frame2, columns=("ID"), show="headings")
tree_sent_sondes.pack()
tree_sent_sondes.heading("ID", text="ID")
tree_sent_sondes.column("ID", width=150, anchor='center')

tk.Label(frame3, text="Settings (config.ini)", font=("Arial", 14), fg='white', bg='black').pack()
config_display = tk.Text(frame3, width=50, height=10, bg='black', fg='white')
config_display.pack()

config = configparser.ConfigParser()
config.read('config.ini')
sender_email = config.get('settings', 'sender_email')
receiver_email = config.get('settings', 'receiver_email')
app_password = config.get('settings', 'app_password')
home_latitude = float(config.get('settings', 'home_latitude'))
home_longitude = float(config.get('settings', 'home_longitude'))
distance_from_home = float(config.get('settings', 'distance_from_home'))
interval = int(config.get('settings', 'interval'))
sonde_view_distance = float(config.get('settings', 'sonde_view_distance'))

def str_to_bool(s):
    return s.strip().lower() == 'true'

send_email_enabled = str_to_bool(config.get('settings', 'send_email', fallback='True'))
send_decoder_enabled = str_to_bool(config.get('settings', 'send_decoder', fallback='True'))

config_data = (
    f"Sender Email: {sender_email}\n"
    f"Receiver Email: {receiver_email}\n"
    f"Home Latitude: {home_latitude}\n"
    f"Home Longitude: {home_longitude}\n"
    f"Distance from Home: {distance_from_home} km\n"
    f"Interval: {interval} s\n"
    f"Sonde View Distance: {sonde_view_distance} km\n"
    f"Send Email: {send_email_enabled}\n"
    f"Send to decoder: {send_decoder_enabled}\n"
)
config_display.insert(tk.END, config_data)
config_display.configure(state='disabled')

sent_sondes_file = 'sent_sondes.txt'

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def send_email(sonde_id, typ, date_time, latitude, longitude, course, speed, altitude, climb, launch, frequency, distance):
    subject = f"Sonde {sonde_id} within {distance:.2f} km from Home position"
    body = (
        f"Sonde ID: {sonde_id}\n"
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
        f"Distance from Home location: {distance:.2f} km\n"
    )
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

def email_sent(sonde_id):
    try:
        with open(sent_sondes_file, 'r') as file:
            sent_sondes = file.read().splitlines()
        return sonde_id in sent_sondes
    except FileNotFoundError:
        return False

last_update_label = tk.Label(root, text="Last update: N/A", font=("Arial", 12), fg='white', bg='black')
last_update_label.grid(row=2, column=0, columnspan=2)

status_label = tk.Label(root, text="Status: Waiting for the first data fetch...", font=("Arial", 12), fg='yellow', bg='black')
status_label.grid(row=3, column=0, columnspan=2)

def process_data():
    url = 'https://radiosondy.info/dyn/get_flying.php'
    headers = {'User-Agent': 'Mozilla/5.0'}

    status_label.config(text="Status: Fetching data from Radiosondy.info...", fg='yellow')

    while True:
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                table = soup.find('table')
                rows = table.find_all('tr')[1:]  # skip header
                data = []
                for row in rows:
                    cols = [td.get_text(strip=True) for td in row.find_all('td')]
                    if len(cols) >= 11:
                        data.append(cols)
                status_label.config(text="Status: Data fetched successfully!", fg='green')
                break
            else:
                raise Exception(f"Error {response.status_code}")
        except Exception as e:
            print(f"Error: {e}, retrying in 30s...")
            status_label.config(text="Status: Error fetching data. Retrying in 30 seconds...", fg='red')
            time.sleep(30)

    tree_sondes.delete(*tree_sondes.get_children())

    for row in data:
        sonde_id, typ, date_time, lat, lon, course, speed, alt, climb, launch, freq = row[:11]
        try:
            lat = float(lat)
            lon = float(lon)
            distance = haversine(home_latitude, home_longitude, lat, lon)
        except:
            continue

        print(f"Sonde {sonde_id:<12} distance from Home: {distance:.2f} km")
        if distance < sonde_view_distance:
            tree_sondes.insert("", "end", values=(
                sonde_id, typ, date_time, lat, lon, course, speed, alt, climb, launch, freq, f"{distance:.2f} km"
            ))
            if distance < distance_from_home and not email_sent(sonde_id):
                if send_email_enabled:
                    send_email(sonde_id, typ, date_time, lat, lon, course, speed, alt, climb, launch, freq, distance)
                if send_decoder_enabled:
                    clean_freq = freq.replace(" MHz", "")
                    send_command(freq=clean_freq, tip=typ, restart=True)

    adjust_column_widths(tree_sondes)

    tree_sent_sondes.delete(*tree_sent_sondes.get_children())
    try:
        with open(sent_sondes_file, 'r') as file:
            for sent_sonde in file.read().splitlines():
                tree_sent_sondes.insert("", "end", values=(sent_sonde,))
    except FileNotFoundError:
        pass

    dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    last_update_label.config(text=f"Last update: {dt}")

def send_command(freq=None, tip=None, restart=False):
    print(f"[DEBUG send_command] freq={freq!r}, tip={tip!r}, restart={restart}")
    data = {}
    if freq: data["freq"] = freq
    if tip: data["type"] = tip
    if restart: data["restart"] = True
    try:
        s = socket.socket()
        s.connect(("127.0.0.1", 65432))
        s.sendall(json.dumps(data).encode())
        response = s.recv(1024).decode().strip()
        print("[CLIENT] Response:", response)
        s.close()
    except Exception as e:
        print("[CLIENT] Failed to send:", e)

def start_processing():
    process_data()
    root.after(interval * 1000, start_processing)

exit_button = tk.Button(root, text="Exit", command=root.quit, bg='red', fg='white', font=("Arial", 26))
exit_button.grid(row=5, column=0, columnspan=2, pady=10)

start_processing()
root.mainloop()
