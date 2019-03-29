# Standard library
import os
import time
import math, random # Needed for test values
from sqlite3 import connect

# PIP
import psutil


DB_FILE = "/var/ramdisk/data.db"
TIME_STEP = 10.0
MAX_AGE = 60 * 60 * 24 # in seconds

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
    entries["RAM Disk"] = psutil.disk_usage('/var/ramdisk').percent

    category["entries"] = entries
    data["storage"] = category


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

        print(delta)
        # print(".", end="", flush=True)
        time.sleep(max(0, TIME_STEP - delta))
