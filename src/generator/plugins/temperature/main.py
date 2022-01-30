import psutil
from generator import create_category_entry
from pluginconfig import Config


# Interface
def get_entries():
    return _get_temperature_entries()

def get_config():
    category_title = "Temperature"
    sleep_duration = 10

    config = Config(category_title, sleep_duration)

    return config


# Internal functions
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
