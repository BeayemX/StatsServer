import psutil
from generator import create_category_entry
from pluginconfig import Config


# Interface
def get_entries():
    return _get_disk_entries()

def get_config():
    category_title = "Storage"
    sleep_duration = 30

    config = Config(category_title, sleep_duration)

    return config


# Internal functions
def _get_disk_entries():
    entries = {}
    # disks = [("Disk", "/"), ]
    disks = []

    for disk in psutil.disk_partitions():
        name = disk.device
        path = disk.mountpoint
        # usage = psutil.disk_usage(path)
        disks.append((name, path))


    for name, path in disks:
        # entries[name] = create_category_entry(psutil.disk_usage(path).used, "byte", 0, psutil.disk_usage(path).total)
        entries[name] = create_category_entry(psutil.disk_usage(path).percent, " %")

    return entries