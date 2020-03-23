# Standard library
import sys
import os
import threading
import traceback
import time
import math, random, datetime # Needed for test values

# PIP
import psutil

# Network
import requests
import json

# Websockets
import asyncio
import websockets

# StatsServer
import config_loader

threads = {}

# Load settings from config file

conf = config_loader.load()

general_conf = conf['general']
generator_conf = conf['generator']
ws_conf = conf['server']['websocket']


NETWORK_TIME_STEP = 10

MAX_NETWORK_SPEED = generator_conf['max_network_speed']
MAX_NETWORK_SPEED *= NETWORK_TIME_STEP

HOST = generator_conf['host']
PORT = ws_conf['port']
DEBUG = general_conf['debug']

USER_ID = generator_conf['client_id']
PROJECT_ID = generator_conf['project_id']


uri = f"ws://{HOST}:{PORT}"

RECONNECT_TIME = 5
pending_requests = []

# Network variables
sent_byte = psutil.net_io_counters()[0]
received_byte = psutil.net_io_counters()[1]

# Load variables
MAX_LOAD = psutil.cpu_count()

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
    spacing = len(str(len(cpus))) + 1
    for cpu_load in cpus:
        entry = create_category_entry(cpu_load, " %", 0, 100)
        entries[f"CPU{str(counter).rjust(spacing)}"] = entry
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

    for name, path in [("Disk", "/"), ]:
        entries[name] = create_category_entry(psutil.disk_usage(path).used, "byte", 0, psutil.disk_usage(path).total)

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
            "sleep_time": 10.0
        },
        "load": {
            "function": _get_load_entries,
            "sleep_time": 10.0
        },
        "temperature": {
            "function": _get_temperature_entries,
            "sleep_time": 10.0
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

    #for t in threads.values():
        #t.join()

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

            data = {
                "category": category,
                "label": label,
                "value": value
            }

            upload_data(data)

        # Finish frame
        end_time = time.time()
        delta = end_time - start_time

        actual_sleep_time = max(0, sleep_time - delta)

        if DEBUG:
            print(thread_id.ljust(32), str(delta))

        time.sleep(actual_sleep_time)

def upload_data(data):
    data["userid"] = USER_ID
    data["project"] = PROJECT_ID
    # data["type"] = "add_value"

    pending_requests.append(data)

async def main():
    global pending_requests
    async with websockets.connect(uri) as websocket:
        async def send(data):
            await websocket.send(json.dumps(data))
        print("Connection established")
        while True:
            working_queue = pending_requests
            pending_requests = []

            for data in working_queue:
                await send(data)
            await asyncio.sleep(1)


try:
    multi_thread_gathering()
except KeyboardInterrupt:
    print("\nStopped via KeyboardInterrupt.")

while True:
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except ConnectionRefusedError:
        now = datetime.datetime.now()
        print(f"Connection refused: {now.strftime('%Y-%m-%d_%H:%M:%S')}")
        time.sleep(RECONNECT_TIME)
    except KeyboardInterrupt:
        print("Exiting")
        sys.exit(0)
    except Exception as e:
        print(e)

