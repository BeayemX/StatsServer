import psutil
from generator import create_category_entry
from pluginconfig import Config


# Constants
NETWORK_TIME_STEP = 10  # seconds
MAX_NETWORK_SPEED = 5767168 * NETWORK_TIME_STEP  # bytes per sec


# Network variables
class TrafficBytes:
    def __init__(self) -> None:
        self.sent_byte = psutil.net_io_counters()[0]
        self.received_byte = psutil.net_io_counters()[1]


# Variables
GlobalBytes = TrafficBytes()


# Interface
def get_entries():
    return _get_network_entries()

def get_config():
    category_title = "Network"
    sleep_duration = NETWORK_TIME_STEP

    config = Config(category_title, sleep_duration)

    return config



# Internal functions
def _get_network_entries():
    entries = {}

    #nics = psutil.net_if_stats()
    #for nic in nics:
        #print(nic, nics[nic])

    new_sent = psutil.net_io_counters()[0]
    new_received = psutil.net_io_counters()[1]

    # Calculate delta
    delta_sent = new_sent - GlobalBytes.sent_byte
    delta_received = new_received - GlobalBytes.received_byte

    # Store current network stats
    GlobalBytes.sent_byte = new_sent
    GlobalBytes.received_byte = new_received

    entries["Sent"] = create_category_entry(delta_sent, "byte", 0, MAX_NETWORK_SPEED / 3)
    entries["Received"] = create_category_entry(delta_received, "byte", 0, MAX_NETWORK_SPEED)

    return entries
