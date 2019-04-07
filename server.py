# Standard library
import os
import sys
import time
import socket
import json
import configparser

# PIP
import psutil

# Flask
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, send, emit

# Stats Server
from generator import get_values_for_label, gather_data


# Load settings from config file
conf = configparser.ConfigParser()
conf.read(os.path.join(os.path.dirname(__file__),"settings.conf"))
PORT = conf["Server"].getint("Port")
DEBUG = conf["Server"].getboolean("Debug")

# Initialize server
app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['DEBUG'] = DEBUG

socketio = SocketIO(app, async_mode='eventlet')


def get_data_as_json(last_server_sync_timestamp):
    gathered_data = gather_data()
    data = {}
    categories = {}

    for category_key, category_data in gathered_data.items():
        # to copy 'settings' and so on...
        # # this also provides 'value' entry with just the current value
        # 'values' contains only legacy values from the database
        category = category_data

        entries = {}

        for key in category_data["entries"].keys():
            entries[key] = category_data["entries"][key] # copy every member, e.g. unit, max, min, ...
            entries[key]["values"] = get_values_for_label(category_key, key, last_server_sync_timestamp)

        category["entries"] = entries

        categories[category_key] = category

    data["categories"] = categories

    # Add additional information
    data["last_server_sync_timestamp"] = time.time()

    # Create JSON to calculate size
    return_json = json.dumps(data)

    size = sys.getsizeof(return_json)

    return_json = return_json.rstrip('}') # open json
    return_json +=', "size": ' + str(size) # add size information
    return_json += '}' # close json

    print("Transferring: ", round(size / 1024 / 1024 * 1000) / 1000, "MB")

    return return_json

@app.route('/')
def index():
    return render_template("index.html", hostname = socket.gethostname(), data = get_data_as_json(0))

@socketio.on('request_data')
def handle_my_custom_event(json_data):
    ts = json_data["last_server_sync_timestamp"]
    try:
        ts = int(ts)
    except ValueError:
        ts = 0

    emit("update_data", get_data_as_json(ts))

if __name__ == '__main__':
	socketio.run(app, host='0.0.0.0', port=PORT)