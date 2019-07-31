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


def add_database_entry(cursor, current_time, category, label, value):
    sql = 'INSERT INTO data (category, label, time, value) values(?, ?, ?, ?)'
    args = (category, label, current_time, value)
    cursor.execute(sql, args)

def add_database_process_entry(cursor, time, name, cpu, mem):
    sql = 'INSERT INTO processes (time, name, cpu, memory) values(?, ?, ?, ?)'
    args = (time, name, cpu, round(mem, 2))
    cursor.execute(sql, args)

def clean_up_database(cursor):
    current_time = time.time()

    sql = 'DELETE FROM data WHERE ROWID IN (SELECT ROWID FROM data WHERE time < ?)'
    args = (current_time - MAX_AGE, )
    cursor.execute(sql, args)

    sql = 'DELETE FROM processes WHERE time < ?'
    args = (current_time - MAX_AGE, )
    cursor.execute(sql, args)

def get_values_for_label(category, label, last_server_sync_timestamp):
    with connect(f"file:{DB_FILE}?mode=ro", uri=True) as conn:
        cursor = conn.cursor()
        sql = 'SELECT time, value FROM data WHERE category=? AND label=? AND time > ?'
        args = (category, label, last_server_sync_timestamp)
        cursor.execute(sql, args)
        data = cursor.fetchall()

        if USE_DELTA_COMPRESSION:
            curr_entry = data[0]
            data_list = []
            data_list.append([curr_entry[0], curr_entry[1]])

            ignore_first_value =  True
            delta_values = None

            for d in data:
                if ignore_first_value:
                    ignore_first_value = False
                    continue

                delta_values = []
                for i in range(len(curr_entry)):
                    curr_val = round(d[i] - curr_entry[i], 2)
                    if curr_val == int(round(curr_val)):
                        curr_val = int(round(curr_val))
                    delta_values.append(curr_val)

                curr_entry = d
                data_list.append(delta_values)

            return data_list
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

    for speed in [1.0, 3.0, 10.0, 60.0, 60.0 * 10]:
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
    category = create_category("draw_individual_limits", "draw_outer_limit_min", "draw_outer_limit_max")

    max_value = psutil.cpu_count()

    category["min"] = 0
    category["max"] = max_value
    category["unit"] = ""

    loads = os.getloadavg()

    category["entries"]["Load 1"] = create_category_entry(loads[0], "", 0, max_value)
    category["entries"]["Load 5"] = create_category_entry(loads[1], "", 0, max_value)
    category["entries"]["Load 15"] = create_category_entry(loads[2], "", 0, max_value)

    data["load"] = category

def add_cpu_entries(data):
    category = create_category("draw_global_limit_max", "process_list")
    category["min"] = 0
    category["max"] = 100
    category["unit"] = " %"

    cpus = psutil.cpu_percent(percpu = True)
    counter = 0
    for cpu_load in cpus:
        entry = create_category_entry(cpu_load, " %", 0, 100)
        category["entries"][f"CPU{counter}"] = entry
        counter +=1

    data["processors"] = category

def add_temperature_entries(data):
    category = create_category("draw_global_limit_min", "draw_global_limit_max")
    category["min"] = 35
    category["max"] = 100
    category["unit"] = "°C"

    for name, temps in psutil.sensors_temperatures().items():
        for entry_name in temps:
            label = entry_name.label
            if not label:
                label = name

            entry = create_category_entry(entry_name.current, "°C", 35, 100)
            category["entries"][label] = entry

    data["temperatures"] = category

def add_memory_entries(data):
    category = create_category("draw_individual_limits", "process_list")

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

    category = create_category("draw_individual_limit_max")

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

    # Sent value
    entry = create_category_entry(delta_sent, "byte", 0, MAX_NETWORK_SPEED / 3)
    category["entries"]["Sent"] = entry

    # Received value
    entry = create_category_entry(delta_received, "byte", 0, MAX_NETWORK_SPEED)
    category["entries"]["Received"] = entry

    data["Network"] = category

def gather_process_list():
    process_list = []
    for proc in psutil.process_iter():
        try:
            p_dict = proc.as_dict(attrs=["name", "cpu_percent", "memory_percent"])
            process_list.append((p_dict["name"], p_dict["cpu_percent"], p_dict["memory_percent"])) # create list instead of using dict to make it hashable to be able to create a set later on

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # return process_list

    cpu_list = sorted(process_list, key=lambda process: process[1], reverse=True)
    mem_list = sorted(process_list, key=lambda process: process[2], reverse=True)

    cpu_list = cpu_list[:10]
    mem_list = mem_list[:10]

    # only unique entries
    process_list = cpu_list + mem_list
    process_list = set(process_list)

    return process_list

def get_process_list(category, time):
    data = {}
    with connect(f"file:{DB_FILE}?mode=ro", uri=True) as conn:
        cursor = conn.cursor()
        sql = 'SELECT time, name, cpu, memory FROM processes WHERE time > ?'
        args = (time, )
        cursor.execute(sql, args)
        data = cursor.fetchall()
        """
        sql = 'SELECT DISTINCT time FROM processes WHERE time > ?'
        processes_timestamps = cursor.fetchall()
        for process_timestamp in processes_timestamps:
            process_timestamp = process_timestamp[0] # TODO not sure if needed
            data[process_timestamp] = get_processes_at_time(cursor, category, process_timestamp)
        """

    return data

def get_processes_at_time(cursor, category, time):
    #print("get_processes_at_time", category, time)
    sql = 'SELECT time, name, ' + category + ' FROM processes WHERE time = ? ORDER BY ' + category + ' DESC LIMIT 5' # FIXME when using '?' instead of string concatenation it would not work and instead of interpreting 'cpu' all float-values would be the string 'cpu'... maybe because forwarding cursor in nested sql process?
    args = (time, )
    cursor.execute(sql, args)
    data = cursor.fetchall()

    return data

# Run main program
if __name__ == "__main__":
    # Initialize
    with connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS data (category STRING, label STRING, time REAL, value REAL)')
        cursor.execute('CREATE TABLE IF NOT EXISTS processes (time REAL, name STRING, cpu REAL, memory REAL)')

    start_time = 0
    end_time = 0
    delta = 0

    while True:
        with connect(DB_FILE) as conn:
            cursor = conn.cursor()

            start_time = time.time()
            data = gather_data()
            # TODO use start_time instead of time.time() in add_database_entry()?
            for category, category_data in data.items():
                for label, value in category_data["entries"].items():
                    # TODO not sure if needed, will be influenced because this value will be generated while gathering every data which will cause high cpu loads...
                    # TODO maybe replace with function that just gathers categories/keys
                    add_database_entry(cursor, start_time, category, label, value["value"])

            process_list = gather_process_list()
            for process in process_list:
                name = process[0]
                cpu = process[1]
                mem = process[2]

                add_database_process_entry(cursor, start_time, name, cpu, mem)

            end_time = time.time()

            delta = end_time - start_time
            clean_up_database(cursor)

        # print(delta)
        # print(".", end="", flush=True)
        time.sleep(max(0, TIME_STEP - delta))
