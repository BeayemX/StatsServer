import sys
import os
import asyncio
import time
import json
import websockets
import threading

from sqlite3 import connect

# StatsServer
from databaseutilities import initialize_database, project_exists, get_project_list_for_user
import config_loader

# Load configuration
conf = config_loader.load()

general_conf = conf['general']
server_conf = conf['server']
generator_conf = conf['generator']

ws_conf = server_conf['websocket']
db_conf = server_conf['database']
frontend_conf = server_conf['frontend']

db_conf = conf['server']['database']

USE_DELTA_COMPRESSION = server_conf['use_delta_compression']

#DB_DIR = db_conf['directory']
#DB_FILE = os.path.join(DB_DIR, db_conf['file_name'])

# Configuration
ADDRESS = '0.0.0.0'

# Load configuration
DEBUG_LOG = general_conf['log']
PORT = ws_conf['port']

CLEAN_UP_INTERVAL = server_conf['cleanup_interval']
MAX_AGE = server_conf['max_age']

DB_DIRECTORY = db_conf['directory']
DB_FILE = db_conf['file_name']
DB_FULL_PATH = os.path.join(DB_DIRECTORY, DB_FILE)


async def handle_messages(websocket, path): # This is executed once per websocket
    print("Websocket connection established")
    # TODO check for uuid login info here?
    try:
        async for message in websocket:
            data = json.loads(message)

            if DEBUG_LOG:
                print(time.time(), json.dumps(data))

            try:
                action_type = data['type']
            except KeyError:  # HACK just add type to generator.py
                print("No data type information provided.")
                continue

            if action_type == 'request_data':
                await request_data(websocket, data)
            elif action_type == 'add_data':
                _add_data_point(data["userid"], data["project"], data["category"], data["label"], data["value"])
            else:
                print(f"No handler for data type {data['type']}")


    except asyncio.streams.IncompleteReadError:
        print("IncompleteReadError")
    except websockets.exceptions.ConnectionClosed:
        print("ConnectionClosed")

async def request_data(websocket, data):
    ts = data['last_server_sync_timestamp']
    project_id = data['projectid']

    statsdata = get_data_as_json(project_id, ts)
    await websocket.send(json.dumps({
        'type': 'update_data',
        'data': statsdata,
    }))


def _add_data_point(userid, projectid, category, label, value):
    timestamp = time.time()
    with connect(DB_FULL_PATH) as conn:
        cursor = conn.cursor()
        sql = 'INSERT INTO data (time, userid, projectid, category, label, value) values(?, ?, ?, ?, ?, ?)'
        args = (timestamp, userid, projectid, category, label, value)
        cursor.execute(sql, args)

        if not project_exists(projectid): # TODO unnecessary check on every call, maybe only do when establishing connection?
            sql = 'INSERT INTO projects (userid, projectid) values(?, ?)'
            args = (userid, projectid)
            cursor.execute(sql, args)
        else:
            pass

        return True
    return False

def thread_clean_up_database():
    while True:
        current_time = time.time()

        # Clean up old entries
        with connect(DB_FULL_PATH) as conn:
            cursor = conn.cursor()
            sql = 'DELETE FROM data WHERE ROWID IN (SELECT ROWID FROM data WHERE time < ?)'
            args = (current_time - MAX_AGE, )
            cursor.execute(sql, args)

        # Clean up empty projects

        with connect(DB_FILE) as conn:
            cursor = conn.cursor()
            sql = 'SELECT userid, projectid FROM projects'
            args = ()
            cursor.execute(sql, args)
            data = cursor.fetchall()

            for entry in data:
                userid = entry[0]
                projectid = entry[1]

                sql = 'SELECT * FROM data WHERE projectid=?'
                args = (projectid, )
                cursor.execute(sql, args)
                data = cursor.fetchall()

                if len(data) == 0:
                    if (DEBUG_LOG):
                        print(projectid, "has been removed from the project list")

                    sql = 'DELETE FROM projects WHERE projectid=?'
                    args = (projectid, )
                    cursor.execute(sql, args)

        # Finalize
        delta_time = time.time() - current_time

        if (DEBUG_LOG):
            print("[ Clean Up ]".ljust(16), str(delta_time))

        time.sleep(CLEAN_UP_INTERVAL)


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

# # # # # # # # # # # # # # # # # # # # # # # # #
print("Setting up database")
initialize_database()

print("Starting clean-up thread")
clean_up_thread = threading.Thread(target=thread_clean_up_database)
clean_up_thread.daemon = True
clean_up_thread.start()
print("Database set up")

print("Starting server on port " + str(PORT))
asyncio.get_event_loop().run_until_complete(websockets.serve(handle_messages, ADDRESS, PORT))

print("Server running.")
asyncio.get_event_loop().run_forever()

