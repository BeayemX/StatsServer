# Standard library
import os
import sys
import time
import socket
import json

# PIP
import psutil

# Flask
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, send, emit

# Stats Server
from generator import get_values_for_label, gather_data


app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['DEBUG'] = True

socketio = SocketIO(app, async_mode='eventlet')

def get_data_as_json(last_server_sync_timestamp):
    gathered_data = gather_data()
    data = {}
    categories = {}

    for category_key, category_data in gathered_data.items():
        category = {}
        category["unit"] = category_data["unit"]
        category["min"] = category_data["min"]
        category["max"] = category_data["max"]
        category["settings"] = category_data["settings"]

        entries = {}

        for key in category_data["entries"].keys():
            entries[key] = get_values_for_label(category_key, key, last_server_sync_timestamp)

        category["entries"] = entries

        categories[category_key] = category

    data["categories"] = categories
    data["last_server_sync_timestamp"] = time.time()

    return_json = json.dumps(data)
    print("Transferring: ", round(sys.getsizeof(return_json) / 1024 / 1024 * 1000) / 1000, "MB")

    return return_json

@app.route('/')
def index():
    return render_template("index.html", hostname = socket.gethostname(), data = get_data_as_json(0))

@socketio.on('request_data')
def handle_my_custom_event(json_data):
    emit("update_data", get_data_as_json(json_data["last_server_sync_timestamp"]))

if __name__ == '__main__':
	socketio.run(app, host='0.0.0.0', port=5050)