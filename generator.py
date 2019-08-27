# Standard library
import os
import threading
import time
import math, random, datetime # Needed for test values
from sqlite3 import connect
import configparser

# PIP
import psutil

# Network
import requests


threads = {}
projectid = ""

# Load settings from config file
conf = configparser.ConfigParser()
conf.read(os.path.join(os.path.dirname(__file__),"settings.conf"))

NETWORK_TIME_STEP = 10

DB_DIRECTORY = conf["Generator"]["DatabaseDirectory"]
DB_FILE = conf["Generator"]["DatabaseName"]
DB_FULL_PATH = os.path.join(DB_DIRECTORY, DB_FILE)

MAX_AGE = conf["Generator"].getfloat("MaxAge") # in seconds
MAX_NETWORK_SPEED = conf["Generator"].getfloat("MaxNetworkSpeed") # in Byte
MAX_NETWORK_SPEED *= NETWORK_TIME_STEP
USE_DELTA_COMPRESSION = conf["General"].getboolean("UseDeltaCompression")

REST_PORT = conf["REST Server"].getint("Port")
DEBUG = conf["Server"].getboolean("Debug")

REST_COMMUNICATION = conf["Generator"].getboolean("CommunicateOverRest")

HOST="localhost"
PROJECT_NAME = "StatsServer"

# Network variables
sent_byte = psutil.net_io_counters()[0]
received_byte = psutil.net_io_counters()[1]


# Load variables
MAX_LOAD = psutil.cpu_count()

# Create database directory if it does not exist
if not os.path.exists(DB_DIRECTORY):
    os.makedirs(DB_DIRECTORY)


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

def create_category(*settings):
    return {
        "entries": {},
        "settings": settings,
    }

def create_category_entry(value, unit="", minVal=0, maxVal=100):
    return {
        "value": value,
        "unit": unit,
        "min": minVal,
        "max": maxVal
    }

def add_load_entries(data):
    category = create_category("draw_individual_limits", "draw_outer_limit_min", "draw_outer_limit_max")

    category["min"] = 0
    category["max"] = MAX_LOAD
    category["unit"] = ""

    category["entries"] = _get_load_entries()
    data["load"] = category

def _get_load_entries():
    entries = {}
    loads = os.getloadavg()
    entries["Load  1"] = create_category_entry(loads[0], "", 0, MAX_LOAD)
    entries["Load  5"] = create_category_entry(loads[1], "", 0, MAX_LOAD)
    entries["Load 15"] = create_category_entry(loads[2], "", 0, MAX_LOAD)
    return entries

def add_cpu_entries(data):
    category = create_category("draw_global_limit_max")
    category["min"] = 0
    category["max"] = 100
    category["unit"] = " %"

    category["entries"] = _get_cpu_entries()
    data["processors"] = category

def _get_cpu_entries():
    entries = {}

    cpus = psutil.cpu_percent(percpu = True)
    counter = 0
    for cpu_load in cpus:
        entry = create_category_entry(cpu_load, " %", 0, 100)
        entries[f"CPU{counter}"] = entry
        counter +=1

    return entries

def add_temperature_entries(data):
    category = create_category("draw_global_limit_min", "draw_global_limit_max")
    category["min"] = 35
    category["max"] = 100
    category["unit"] = "°C"

    category["entries"] = _get_temperature_entries()
    data["temperature"] = category

def _get_temperature_entries():
    entries = {}
    for name, temps in psutil.sensors_temperatures().items():
        for entry_name in temps:
            label = entry_name.label
            if not label:
                label = name

            entry = create_category_entry(entry_name.current, "°C", 35, 100)
            entries[label] = entry
    return entries

def add_memory_entries(data):
    category = create_category("draw_individual_limits")

    category["entries"] = _get_memory_entries()
    data["memory"] = category

def _get_memory_entries():
    entries = {}
    entries["RAM"] = create_category_entry(psutil.virtual_memory().used, "byte", 0, psutil.virtual_memory().total)
    entries["Swap"] = create_category_entry(psutil.swap_memory().used, "byte", 0, psutil.swap_memory().total)
    return entries

def add_disk_entries(data):
    category = create_category("nograph") # use psutil.disk_usage('/home/').total?

    category["entries"] = _get_disk_entries()
    data["storage"] = category

def _get_disk_entries():
    entries = {}

    for name, path in [("Disk", "/"), ("Ram disk", DB_DIRECTORY)]:
        entries[name] = create_category_entry(psutil.disk_usage(path).used, "byte", 0, psutil.disk_usage(path).total)

    entries["DB file size"] = create_category_entry(os.path.getsize(DB_FULL_PATH), "byte", 0, psutil.disk_usage(DB_DIRECTORY).total)

    return entries

def add_network_entries(data):
    category = create_category("draw_individual_limit_max")

    category["entries"] = _get_network_entries()
    data["network"] = category

def _get_network_entries():
    global sent_byte
    global received_byte
    entries = {}

    #nics = psutil.net_if_stats()
    #for nic in nics:
        #print(nic, nics[nic])

    new_sent = psutil.net_io_counters()[0]
    new_received = psutil.net_io_counters()[1]

    # Calculate delta
    delta_sent = new_sent - sent_byte
    delta_received = new_received - received_byte

    # Store current network stats
    sent_byte = new_sent
    received_byte = new_received

    entries["Sent"] = create_category_entry(delta_sent, "byte", 0, MAX_NETWORK_SPEED / 3)
    entries["Received"] = create_category_entry(delta_received, "byte", 0, MAX_NETWORK_SPEED)
    return entries


def multi_thread_gathering():
    functions = {
        "processors": {
            "function": _get_cpu_entries,
            "sleep_time": 2.0
        },
        "load": {
            "function": _get_load_entries,
            "sleep_time": 5.0
        },
        "temperature": {
            "function": _get_temperature_entries,
            "sleep_time": 5.0
        },
        "memory": {
            "function": _get_memory_entries,
            "sleep_time": 10.0
        },
        "storage": {
            "function": _get_disk_entries,
            "sleep_time": 30.0
        },
        "network": {
            "function": _get_network_entries,
            "sleep_time": NETWORK_TIME_STEP
        }
    }

    for category, element in functions.items():
        thread_id = f"[ {category.capitalize()} ]"
        func = element["function"]
        sleep_time = element["sleep_time"]
        t = threading.Thread(target=thread_gathering, args=(func, thread_id, category, sleep_time))
        threads[thread_id] = t

    for t in threads.values():
        t.daemon = True
        t.start()

    for t in threads.values():
        t.join()

def thread_gathering(func, thread_id, category, sleep_time):
    start_time = 0
    end_time = 0
    delta = 0

    while True:
        # Get data
        start_time = time.time()

        entries = func()

        # Write data
        for label, label_entry in entries.items():
            value = label_entry["value"]

            if REST_COMMUNICATION:
                call_rest_api(projectid, category, label, value)
            else:
                write_to_db(projectid, category, label, value)

        # Finish frame
        end_time = time.time()
        delta = end_time - start_time

        actual_sleep_time = max(0, sleep_time - delta)

        if DEBUG:
            print(thread_id.ljust(32), str(delta))

        time.sleep(actual_sleep_time)

def write_to_db(projectid, category, label, value):
    with connect(DB_FULL_PATH) as conn:
        cursor = conn.cursor()
        add_database_entry(cursor, projectid, category, label, value)

def get_projectid():
    global projectid

    file_name = "projectid"

    if os.path.exists(file_name):
        with open(file_name, 'r') as f:
            projectid = f.read()
            print("Read project id: ", projectid)
    else:
        URL = f"http://{HOST}:{REST_PORT}/register?name={PROJECT_NAME}"
        response = requests.get(URL)
        projectid = response.content.decode('UTF-8')

        print("Registered", projectid)

        with open(file_name, 'w') as f:
            f.write(projectid)

def call_rest_api(projectid, category, label, value):
    URL = f"http://{HOST}:{REST_PORT}/add_data_point?projectid={projectid}&category={category}&label={label}&value={value}"
    response = requests.get(URL)
    # print(URL, "__response__", response)


# Run main program
if __name__ == "__main__":
    if not REST_COMMUNICATION:
        with connect(DB_FULL_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE IF NOT EXISTS data (projectid STRING, category STRING, label STRING, time REAL, value REAL)')
            cursor.execute('CREATE INDEX IF NOT EXISTS category_index ON data (projectid, category, label, time)')
    # Initialize
    #non_thread_gathering()
    try:
        get_projectid()
        multi_thread_gathering()
    except KeyboardInterrupt:
        print("\nStopped via KeyboardInterrupt.")
