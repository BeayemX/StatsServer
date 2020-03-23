import sys
import os
import asyncio
import time
import json
import websockets
import configparser
import threading
from sqlite3 import connect

# StatsServer
from databaseutilities import initialize_database, project_exists, get_project_list_for_user
import config_loader

# Configuration
ADDRESS = '0.0.0.0'

# Load configuration
conf = config_loader.load()
general_conf = conf['general']
server_conf = conf['server']
ws_conf = server_conf['websocket']
db_conf = server_conf['database']


DEBUG = general_conf['debug']
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
            if DEBUG:
                print(json.dumps(data))
            _add_data_point(data["userid"],data["project"],data["category"],data["label"],data["value"])
    except asyncio.streams.IncompleteReadError:
        print("IncompleteReadError")
    except websockets.exceptions.ConnectionClosed:
        print("ConnectionClosed")

def _add_data_point(userid, projectid, category, label, value):
    timestamp = time.time()
    with connect(DB_FULL_PATH) as conn:
        cursor = conn.cursor()
        sql = 'INSERT INTO data (time, projectid, category, label, value) values(?, ?, ?, ?, ?)'
        args = (timestamp, projectid, category, label, value)
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
                    if (DEBUG):
                        print(projectid, "has been removed from the project list")

                    sql = 'DELETE FROM projects WHERE projectid=?'
                    args = (projectid, )
                    cursor.execute(sql, args)

        # Finalize
        delta_time = time.time() - current_time

        if (DEBUG):
            print("[ Clean Up ]".ljust(16), str(delta_time))

        time.sleep(CLEAN_UP_INTERVAL)

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