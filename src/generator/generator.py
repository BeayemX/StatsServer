# Standard library
import threading
import time
import json

# Loading plugins
import importlib
from os import listdir

# Custom
from websocketserver import Globals  # To share data with WebSocketServer


# Load config
with open('config.json') as f:
    conf = json.load(f)


# Constants
USER_ID = conf['client_id']
PROJECT_ID = conf['project_id']
DEBUG = conf['debug']


# Variables
threads = {}


# Functions
def create_category_entry(value, unit="", minVal=0, maxVal=100):
    return {
        "value": value,
        "unit": unit,
        "min": minVal,
        "max": maxVal
    }


def load_plugins():
    addon_directory = 'plugins'
    plugins = listdir(addon_directory)

    plugin_modules = []

    for plugin_name in plugins:
        path = f"{addon_directory}.{plugin_name}.main"
        mod = importlib.import_module(path)

        plugin_modules.append(mod)

    return plugin_modules


def create_threads_for_plugins(modules):
    for module in modules:
        # Module config
        module_config = module.get_config()

        # Prepare arguments
        func = module.get_entries
        sleep_time = module_config.sleep_duration
        category_name = module_config.name
        thread_id = f"[ {category_name.capitalize()} ]"

        # Create thread
        t = threading.Thread(target=thread_gathering, args=(func, thread_id, category_name, sleep_time))
        threads[thread_id] = t

    # Start all threads
    for t in threads.values():
        t.daemon = True
        t.start()


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
    data['type'] = 'add_data'

    Globals.pending_requests.append(data)


def start():
    print("Generator started.")
    plugins = load_plugins()
    create_threads_for_plugins(plugins)
