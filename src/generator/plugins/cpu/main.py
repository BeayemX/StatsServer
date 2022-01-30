import psutil
from generator import create_category_entry
from pluginconfig import Config


# Interface
def get_entries():
    return _get_cpu_entries()


def get_config():
    category_title = "Processors"
    sleep_duration = 10

    config = Config(category_title, sleep_duration)

    return config


# Internal functions
def _get_cpu_entries():
    entries = {}

    cpus = psutil.cpu_percent(percpu=True)
    counter = 0
    spacing = len(str(len(cpus))) + 1

    for cpu_load in cpus:
        entry = create_category_entry(cpu_load, " %", 0, 100)
        entries[f"CPU{str(counter).rjust(spacing)}"] = entry

        counter += 1

    return entries

