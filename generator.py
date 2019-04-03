# Standard library
import os
import time
import math, random # Needed for test values
from sqlite3 import connect
import configparser

# PIP
import psutil


# Load settings from config file
conf = configparser.ConfigParser()
conf.read(os.path.join(os.path.dirname(__file__),"settings.conf"))

DB_DIR = conf["Generator"]["DatabaseDirectory"]
DB_FILE = os.path.join(DB_DIR, conf["Generator"]["DatabaseName"])
TIME_STEP = conf["Generator"].getfloat("Timestep")
MAX_AGE = conf["Generator"].getfloat("MaxAge") # in seconds
MAX_NETWORK_SPEED = conf["Generator"].getfloat("MaxNetworkSpeed") # in MByte
MAX_NETWORK_SPEED *= TIME_STEP

# Network variables
sent_byte = psutil.net_io_counters()[0]
received_byte = psutil.net_io_counters()[1]

# Create database directory if it does not exist
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)


def add_database_entry(cursor, category, label, value):
    current_time = time.time()
    sql = 'INSERT INTO data (category, label, time, value) values(?, ?, ?, ?)'
    args = (category, label, current_time, value)
    cursor.execute(sql, args)

def clean_up_database(cursor):
    current_time = time.time()
    sql = 'DELETE FROM data WHERE ROWID IN (SELECT ROWID FROM data WHERE time < ?)'
    args = (current_time - MAX_AGE, )
    cursor.execute(sql, args)

def get_values_for_label(category, label, last_server_sync_timestamp):
    with connect(f"file:{DB_FILE}?mode=ro", uri=True) as conn:
        cursor = conn.cursor()
        sql = 'SELECT time, value FROM data WHERE category=? AND label=? AND time > ?'
        args = (category, label, last_server_sync_timestamp)
        cursor.execute(sql, args)
        data = cursor.fetchall()
        return data

def gather_data():
    data = {}
    # add_sinus_entries(data) # Testing
    # add_random_entries(data) # Testing
    add_cpu_entries(data)
    add_load_entries(data)
    add_temperature_entries(data)
    add_memory_entries(data)
    add_disk_entries(data)
    add_network_entries(data)

    return data

def create_category(unit, min_value, max_value):
    # FIXME when changing something here, code must also be adjusted
    # in server.py
    # just before sending to server, every entry is duplicated by hand...
    return {
        "unit": unit,
        "min": min_value,
        "max": max_value,
        "settings": []
    }

def add_sinus_entries(data):
    category = create_category("", -1.5, 1.5)

    curr_time = time.time()

    entries = {}
    entries["Sine1"] = math.sin(curr_time)
    entries["Sine3"] = math.sin(curr_time / 3.0)
    entries["Sine10"] = math.sin(curr_time / 10.0)

    category["entries"] = entries
    data["Test values"] = category

def add_random_entries(data):
    category = create_category("", -0.5, 1.5)

    entries = {}
    for i in range(8):
        rand_value = 1
        for j in range(i):
             rand_value *= random.random()
        entries[f"Random{i}"] = rand_value

    category["entries"] = entries
    data["Random values"] = category

def add_load_entries(data):
    category = create_category("", 0, psutil.cpu_count())

    entries = {}
    entries["Load"] = os.getloadavg()[0]

    category["entries"] = entries
    data["load"] = category

def add_cpu_entries(data):
    category = create_category(" %", 0, 100)

    entries = {}

    cpus = psutil.cpu_percent(percpu = True)
    counter = 0
    for cpu_load in cpus:
        entries[f"CPU{counter}"] = cpu_load
        counter +=1

    category["entries"] = entries
    data["processors"] = category

def add_temperature_entries(data):
    category = create_category("°C", 35, 100)

    entries = {}
    for name, temps in psutil.sensors_temperatures().items():
        for entry in temps:
            label = entry.label
            if not label:
                label = name
            entries[label] = entry.current

    category["entries"] = entries
    data["temperatures"] = category

def add_memory_entries(data):
    category = create_category(" %", 0, 100)

    entries = {}
    entries["RAM"] = psutil.virtual_memory().percent
    entries["Swap"] = psutil.swap_memory().percent

    category["entries"] = entries
    data["memory"] = category

def add_disk_entries(data):
    category = create_category(" %", 0, 100) # use psutil.disk_usage('/home/').total?
    category["settings"].append("nograph")

    entries = {}
    entries["Disk"] = psutil.disk_usage('/').percent
    entries["DB Directory"] = psutil.disk_usage(DB_DIR).percent

    category["entries"] = entries
    data["storage"] = category

def add_network_entries(data):
    global sent_byte
    global received_byte

    category = create_category(" MB", 0, MAX_NETWORK_SPEED)

    #nics = psutil.net_if_stats()
    #for nic in nics:
        #print(nic, nics[nic])

    new_sent = psutil.net_io_counters()[0]
    new_received = psutil.net_io_counters()[1]

    # Calculate delta
    delta_sent = new_sent - sent_byte
    delta_received = new_received - received_byte

    # Convert to MB
    delta_sent /= 1024 * 1024
    delta_received /= 1024 * 1024

    # Round to 3 decimals
    delta_sent = round(delta_sent * 1000) / 1000
    delta_received = round(delta_received * 1000) / 1000

    # Store current network stats
    sent_byte = new_sent
    received_byte = new_received

    entries = {}
    entries["Sent"] = delta_sent
    entries["Received"] = delta_received

    category["entries"] = entries
    data["Network"] = category


# Run main program
if __name__ == "__main__":
    # Initialize
    with connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS data (category STRING, label STRING, time REAL, value REAL)')

    start_time = 0
    end_time = 0
    delta = 0

    while True:
        with connect(DB_FILE) as conn:
            cursor = conn.cursor()

            start_time = time.time()
            data = gather_data()
            for category, category_data in data.items():
                for label, value in category_data["entries"].items():
                    add_database_entry(cursor, category, label, value)

            end_time = time.time()

            delta = end_time - start_time
            clean_up_database(cursor)

        # print(delta)
        # print(".", end="", flush=True)
        time.sleep(max(0, TIME_STEP - delta))
