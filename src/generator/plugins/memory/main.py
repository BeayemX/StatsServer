import psutil
from generator import create_category_entry
from pluginconfig import Config


# Interface
def get_entries():
    return _get_memory_entries()

def get_config():
    category_title = "Memory"
    sleep_duration = 10

    config = Config(category_title, sleep_duration)

    return config

# Internal functions
def _get_memory_entries():
    entries = {}
    # entries["RAM"] = create_category_entry(psutil.virtual_memory().used, "byte", 0, psutil.virtual_memory().total)
    # entries["Swap"] = create_category_entry(psutil.swap_memory().used, "byte", 0, psutil.swap_memory().total)

    entries["RAM"] = create_category_entry(psutil.virtual_memory().percent, " %")
    entries["Swap"] = create_category_entry(psutil.swap_memory().percent, " %")

    return entries
