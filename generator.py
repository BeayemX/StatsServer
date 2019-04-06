# Standard library
import os
import time
import math, random, datetime # Needed for test values
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
    # add_linear_entries(data) # Testing

    add_cpu_entries(data)
    add_load_entries(data)
    add_temperature_entries(data)
    add_memory_entries(data)
    add_disk_entries(data)
    add_network_entries(data)

    return data

def create_category(*settings):
    return {
        "entries": {},
        "settings": settings,
    }

def create_category_entry(value, unit="", min=0, max=100):
    return {
        "value": value,
        "unit": unit,
        "min": min,
        "max": max
    }

def add_sinus_entries(data):
    category = create_category()

    curr_time = time.time()

    for speed in [1.0, 3.0, 10.0]:
        value = math.sin(curr_time / speed)
        entry = create_category_entry(value, "", -1.5, 1.5)
        category["entries"][f"Sine{int(speed)}"] = entry

    data["Test values"] = category

def add_random_entries(data):
    category = create_category()

    for i in range(8):
        rand_value = 1
        for j in range(i):
             rand_value *= random.random()

        entry = create_category_entry(rand_value, "", -0.5, 1.5)
        category["entries"][f"Random{i}"] = entry

    data["Random values"] = category

def add_linear_entries(data):
    category = create_category()

    now = datetime.datetime.now()

    # Hour
    entry = create_category_entry(now.hour, "h", 0, 24)
    category["entries"]["Hours"] = entry

    # Minute
    entry = create_category_entry(now.minute, "m", 0, 60)
    category["entries"]["Minutes"] = entry

    # Second
    entry = create_category_entry(now.second, "m", 0, 60)
    category["entries"]["Seconds"] = entry

    data["Time"] = category

def add_load_entries(data):
    category = create_category()

    entry = create_category_entry(os.getloadavg()[0], "", 0, psutil.cpu_count())
    category["entries"]["Load"] = entry

    data["load"] = category

def add_cpu_entries(data):
    category = create_category()

    cpus = psutil.cpu_percent(percpu = True)
    counter = 0
    for cpu_load in cpus:
        entry = create_category_entry(cpu_load, " %", 0, 100)
        category["entries"][f"CPU{counter}"] = entry
        counter +=1

    data["processors"] = category

def add_temperature_entries(data):
    category = create_category()

    for name, temps in psutil.sensors_temperatures().items():
        for entry_name in temps:
            label = entry_name.label
            if not label:
                label = name

            entry = create_category_entry(entry_name.current, "°C", 35, 100)
            category["entries"][label] = entry

    data["temperatures"] = category

def add_memory_entries(data):
    category = create_category()

    # RAM
    entry = create_category_entry(psutil.virtual_memory().used, "byte", 0, psutil.virtual_memory().total)
    category["entries"]["RAM"] = entry

    # Swap
    entry = create_category_entry(psutil.swap_memory().used, "byte", 0, psutil.swap_memory().total)
    category["entries"]["Swap"] = entry

    data["memory"] = category

def add_disk_entries(data):
    category = create_category("nograph") # use psutil.disk_usage('/home/').total?

    for name, path in [("Disk", "/"), ("DB Directory", DB_DIR)]:
        entry = create_category_entry(psutil.disk_usage(path).used, "byte", 0, psutil.disk_usage(path).total)
        category["entries"][name] = entry

    data["storage"] = category

def add_network_entries(data):
    global sent_byte
    global received_byte

    category = create_category()

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

    # Sent value
    entry = create_category_entry(delta_sent, " MB", 0, MAX_NETWORK_SPEED / 3.0)
    category["entries"]["Sent"] = entry

    # Received value
    entry = create_category_entry(delta_received, " MB", 0, MAX_NETWORK_SPEED)
    category["entries"]["Received"] = entry

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
                    add_database_entry(cursor, category, label, value["value"])

            end_time = time.time()

            delta = end_time - start_time
            clean_up_database(cursor)

        # print(delta)
        # print(".", end="", flush=True)
        time.sleep(max(0, TIME_STEP - delta))
