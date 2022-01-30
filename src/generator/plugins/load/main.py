import os
import psutil
from generator import create_category_entry
from pluginconfig import Config

# Load variables
MAX_LOAD = psutil.cpu_count()


# Interface
def get_entries():
    return _get_load_entries()

def get_config():
    category_title = "Load"
    sleep_duration = 10

    config = Config(category_title, sleep_duration)

    return config


# Internal functions
def _get_load_entries():
    entries = {}

    loads = os.getloadavg()
    entries["Load  1"] = create_category_entry(loads[0], "", 0, MAX_LOAD)
    entries["Load  5"] = create_category_entry(loads[1], "", 0, MAX_LOAD)
    entries["Load 15"] = create_category_entry(loads[2], "", 0, MAX_LOAD)

    return entries
