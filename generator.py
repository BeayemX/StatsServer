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
MAX_NETWORK_SPEED = conf["Generator"].getfloat("MaxNetworkSpeed") # in Byte
MAX_NETWORK_SPEED *= TIME_STEP
USE_DELTA_COMPRESSION = conf["General"].getboolean("UseDeltaCompression")

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

def create_category_entry(value, unit="", minVal=0, maxVal=100):
    return {
        "value": value,
        "unit": unit,
        "min": minVal,
        "max": maxVal
    }

def add_sinus_entries(data):
    category = create_category()

    curr_time = time.time()

    for speed in [1.0, 3.0, 10.0, 60.0, 60.0 * 10]:
        value = math.sin(curr_time / speed)
        entry = create_category_entry(value, "", -1.5, 1.5)
        category["entries"][f"Sine{int(speed)}"] = entry

    data["test values"] = category

def add_random_entries(data):
    category = create_category()

    for i in range(8):
        rand_value = 1
        for j in range(i):
             rand_value *= random.random()

        entry = create_category_entry(rand_value, "", -0.5, 1.5)
        category["entries"][f"Random{i}"] = entry

    data["random values"] = category

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

    data["time"] = category

def add_load_entries(data):
    category = create_category("draw_individual_limits", "draw_outer_limit_min", "draw_outer_limit_max")

    max_value = psutil.cpu_count()

    category["min"] = 0
    category["max"] = max_value
    category["unit"] = ""

    category["entries"] = _get_load_entries()
    data["load"] = category

def _get_load_entries():
    entries = {}
    loads = os.getloadavg()
    entries["Load 1"] = loads[0] # create_category_entry(loads[0], "", 0, max_value)
    entries["Load 5"] = loads[1] # create_category_entry(loads[1], "", 0, max_value)
    entries["Load 15"] = loads[2] # create_category_entry(loads[2], "", 0, max_value)
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

    for name, path in [("Disk", "/"), ("Ram disk", DB_DIR)]:
        entries[name] = create_category_entry(psutil.disk_usage(path).used, "byte", 0, psutil.disk_usage(path).total)

    entries["DB file size"] = create_category_entry(os.path.getsize(os.path.join(DB_DIR, DB_FILE)), "byte", 0, psutil.disk_usage(DB_DIR).total)

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

def non_thread_gathering():
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
                    # add_database_entry(cursor, category, label, value["value"])
                    try:
                        value = value["value"]
                    except:
                        pass
                    add_database_entry(cursor, category, label, value)


            clean_up_database(cursor)

        end_time = time.time()
        delta = end_time - start_time

        # print(".", end="", flush=True)

        actual_sleep_time = max(0, TIME_STEP - delta)
        print(actual_sleep_time)

        time.sleep(actual_sleep_time)

threads = {}
def multi_thread_gathering():
    import threading
    functions = {
        "processors": {
            "function": _get_cpu_entries,
            "sleep_time": 0.5
        },
        "load": {
            "function": _get_load_entries,
            "sleep_time": 5.0
        },
        "temperature": {
            "function": _get_temperature_entries,
            "sleep_time": 1.0
        },
        "memory": {
            "function": _get_memory_entries,
            "sleep_time": 5.0
        },
        "storage": {
            "function": _get_disk_entries,
            "sleep_time": 30.0
        },
        "network": {
            "function": _get_network_entries,
            "sleep_time": 1.0
        }
    }

    for category, element in functions.items():
        thread_id = f"[ {category.capitalize()} ]"
        func = element["function"]
        sleep_time = element["sleep_time"]
        t = threading.Thread(target=thread_gathering, args=(func, thread_id, category, sleep_time))
        threads[thread_id] = t

    # TODO use list comprehension
    # [t.start() for t in threads.values()]
    # [t.join() for t in threads.values()]
    for t in threads.values():
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
            value = label_entry
            try: # HACK
                value = value["value"]
            except:
                pass

            with connect(DB_FILE) as conn:
                cursor = conn.cursor()
                add_database_entry(cursor, category, label, value)
                #print("writing", thread_id, category, label, value)

        # Finish frame
        end_time = time.time()
        delta = end_time - start_time

        actual_sleep_time = max(0, sleep_time - delta)
        print(thread_id.ljust(32), str(actual_sleep_time))

        time.sleep(actual_sleep_time)


# Run main program
if __name__ == "__main__":
    with connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS data (category STRING, label STRING, time REAL, value REAL)')
        cursor.execute('CREATE INDEX IF NOT EXISTS category_index ON data (category, label, time)')
    # Initialize
    #non_thread_gathering()
    multi_thread_gathering()
