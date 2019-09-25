# Standard library
import os
import sys
import time
import json
import configparser

# PIP
import psutil

# Flask
from flask import Flask, render_template, jsonify, request, abort
from flask_socketio import SocketIO, send, emit

# Stats Server
#from generator import get_values_for_label, USE_DELTA_COMPRESSION
from databaseutilities import project_exists, get_project_id_for_name, get_project_list_for_user, get_id_for_user_pw, register_user

# Database access
from sqlite3 import connect

import hashlib


# Process sys args
import argparse
parser = argparse.ArgumentParser(description="This will show all values that can be toggled. The initial value is gathered from the configuration file(s). The default values are used if there are no files provided.")
parser.add_argument("-c", "--conf", help="toggle the tasks category")
args = parser.parse_args()

conf_path = "settings.conf"

if args.conf and os.path.isfile(args.conf):
    conf_path = args.conf

# Load settings from config file
conf = configparser.ConfigParser()
conf.read(os.path.join(os.path.dirname(__file__), conf_path))

PORT = conf["Server"].getint("Port")
DEBUG = conf["Server"].getboolean("Debug")
USE_DELTA_COMPRESSION = conf["General"].getboolean("UseDeltaCompression")

DB_DIR = conf["Generator"]["DatabaseDirectory"]
DB_FILE = os.path.join(DB_DIR, conf["Generator"]["DatabaseName"])

# Initialize server
app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['DEBUG'] = DEBUG

socketio = SocketIO(app, async_mode='eventlet')

def gather_data(projectid):
    with connect(DB_FILE) as conn:
        cursor = conn.cursor()
        sql = 'SELECT category, label FROM data WHERE projectid=?'
        args = (projectid, )
        cursor.execute(sql, args)
        data = cursor.fetchall()

        category_labels_dict = {}
        for element in data:
            category = element[0]
            label = element[1]
            if not category in category_labels_dict:
                category_labels_dict[category] = set()

            category_labels_dict[category].add(label)

        data = {}
        for category, labels in category_labels_dict.items():
            # print(category)
            data[category] = {
                "entries": {}
            }
            for label in labels:
                # print(f"  {label}")
                data[category]["entries"][label] = {}
        return data
    print("Something went wrong when trying to read database")
    return None

def get_data_as_json(projectid, last_server_sync_timestamp):
    print("> > get_data_as_json")
    gathered_data = gather_data(projectid)
    data = {}
    categories = {}

    for category_key, category_data in gathered_data.items():
        # to copy 'settings' and so on...
        # # this also provides 'value' entry with just the current value
        # 'values' contains only legacy values from the database
        category = category_data

        entries = {}

        for label in category_data["entries"].keys():
            #entries[label] = category_data["entries"][label] # copy every member, e.g. unit, max, min, ...
            entries[label] = {}
            entries[label]["value"] = [time.time(), 0] # FIXME there is no current value
            entries[label]["values"] = get_values_for_label(projectid, category_key, label, last_server_sync_timestamp)
            entries[label]["unit"] = ""
            entries[label]["min"] = 0
            entries[label]["max"] = 100

        category["settings"] = ["draw_global_limits"]
        category["entries"] = entries

        categories[category_key] = category

    data["categories"] = categories

    # Add additional information
    data["last_server_sync_timestamp"] = time.time()
    data["use_delta_compression"] = USE_DELTA_COMPRESSION # FIXME, read USE_DELTA_COMPRESSION from config file

    # Create JSON to calculate size
    return_json = json.dumps(data)

    size = sys.getsizeof(return_json)

    return_json = return_json.rstrip('}') # open json
    return_json +=', "size": ' + str(size) # add size information
    return_json += '}' # close json

    print("Transferring: ", round(size / 1024 / 1024 * 1000) / 1000, "MB")
    return return_json

def get_values_for_label(projectid, category, label, last_server_sync_timestamp):
    with connect(f"file:{DB_FILE}?mode=ro", uri=True) as conn:
        cursor = conn.cursor()
        sql = 'SELECT time, value FROM data WHERE projectid=? AND category=? AND label=? AND time > ?'
        args = (projectid, category, label, last_server_sync_timestamp)
        cursor.execute(sql, args)
        data = cursor.fetchall()

        if data:
            if USE_DELTA_COMPRESSION:
                curr_entry = data[0]
                data_list = []
                data_list.append([curr_entry[0], curr_entry[1]])

                ignore_first_value =  True
                delta_values = None

                for d in data:
                    if ignore_first_value:
                        ignore_first_value = False
                        continue

                    delta_values = []
                    for i in range(len(curr_entry)):
                        curr_val = round(d[i] - curr_entry[i], 2)
                        if curr_val == int(round(curr_val)):
                            curr_val = int(round(curr_val))
                        delta_values.append(curr_val)

                    curr_entry = d
                    data_list.append(delta_values)

                return data_list

        return data

@app.route('/login')
def login():
    return render_template("login.html")

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/projectlist')
def projectlist():    
    return render_template("projectlist.html")

@app.route('/project/<projectname>')
def project(projectname=None):
    projectid = get_project_id_for_name(projectname)
    if project_exists(projectid):
        return render_template("projectview.html", hostname=projectname, projectid=projectid)

    return abort(404)
    # return abort(int(projectid))

@app.route('/post', methods=['POST'])
def post():
    if request.method == 'POST':
        data = request.json
        data_dict = None
        if isinstance(data, str): # already json-string, coming from python
            data_dict = json.loads(data)
            print(json.dumps(data_dict, indent=4, sort_keys=True))
        elif isinstance(data, dict): # coming from JavaScript
            print(json.dumps(data, indent=4, sort_keys=True))
            data_dict = data
        else:
            print("Data is of type:", type(data))


        if data_dict["type"] == "login":
            usr = data_dict["username"]
            pw = data_dict["password"]
            hashed_pw = hash_pw(pw)

            user_id = get_id_for_user_pw(usr, hashed_pw)

            if user_id:
                return json.dumps({
                    "error": 0,
                    "userId": user_id
                })
            else:
                return json.dumps({
                    "error": 1,
                    "errorMessage": "Login failed"
                })

        elif data_dict["type"] == "register":
            usr = data_dict["username"]
            pw = data_dict["password"]

            hashed_pw = hash_pw(pw)
            user_id = register_user(usr, hashed_pw)

            if user_id == None:
                return json.dumps({
                    "error": 1,
                    "errorMessage": "User does already exist"
                })
            else:
                return json.dumps({
                    "error": 0,
                    "userId": user_id
                })


        elif data_dict["type"] == "get_project_list":
            return json.dumps({
                "projects": get_project_list_for_user(data_dict["userId"])
            })

        return json.dumps({
            "type": "server_response",
            "state": "done"
        })
    return "No POST method used"

def hash_pw(pw):
    return hashlib.sha512(str(pw).encode('utf-8')).hexdigest()

@socketio.on('request_data')
def handle_my_custom_event(json_data):
    projectid = json_data["projectid"]
    ts = json_data["last_server_sync_timestamp"]

    print("\n < < < Requesting data from client > > >", ts)
    try:
        ts = int(ts)
    except ValueError:
        ts = 0

    emit("update_data", get_data_as_json(projectid, ts))

if __name__ == '__main__':
	socketio.run(app, host='0.0.0.0', port=PORT)

