from sqlite3 import connect
import configparser
import os
import time
from datetime import datetime

import threading
import uuid

from databaseutilities import project_exists, initialize_database, get_project_list_for_user

conf = configparser.ConfigParser()
conf.read(os.path.join(os.path.dirname(__file__),"settings.conf"))

DEBUG = conf["Server"].getboolean("Debug")
PORT = conf["REST Server"].getint("Port")
CLEAN_UP_INTERVAL = conf["REST Server"].getint("CleanUpInterval")
MAX_AGE = conf["REST Server"].getint("MaxAge")
DB_DIRECTORY = conf["Generator"]["DatabaseDirectory"]
DB_FILE = conf["Generator"]["DatabaseName"]
DB_FULL_PATH = os.path.join(DB_DIRECTORY, DB_FILE)

# Flask
from flask import Flask, render_template, jsonify, request
import json

app = Flask(__name__)
app.config['DEBUG'] = DEBUG

def _add_data_point(userid, projectid, category, label, value):
    timestamp = time.time()
    with connect(DB_FULL_PATH) as conn:
        cursor = conn.cursor()
        sql = 'INSERT INTO data (time, projectid, category, label, value) values(?, ?, ?, ?, ?)'
        args = (timestamp, projectid, category, label, value)
        cursor.execute(sql, args)

        if not project_exists(projectid):
            sql = 'INSERT INTO projects (userid, projectid) values(?, ?)'
            args = (userid, projectid)
            cursor.execute(sql, args)
        return True
    return False


@app.route('/post', methods=['POST'])
def post():
    if request.method != 'POST':
        print("Not a POST method")
        return

    # Extract POST data
    data = request.json
    data_dict = None
    if isinstance(data, str): # already json-string, coming from python
        data_dict = json.loads(data)
        #print(json.dumps(data_dict, indent=4, sort_keys=True))
    elif isinstance(data, dict): # coming from JavaScript
        data_dict = data
        #print(json.dumps(data_dict, indent=4, sort_keys=True))
    else:
        print("Data is of type:", type(data))

    # Handle request
    return_data = {
        "error": 0,
        "message": "Success"
    }
    
    msgtype = data_dict["type"]
    if msgtype == "create_project":
        pass
    elif msgtype == "create_category":
        # TODO check if project exists
        # error_message = "Project does not exist"
        pass
    elif msgtype == "create_entry":
        # TODO check if category exists
        # error_message = "Category does not exist"
        pass
    elif msgtype == "add_value":
        # TODO check if entry exists
        # error_message = "Entry does not exist"
        completed_successfully = _add_data_point(
            data_dict["userid"],
            data_dict["project"],
            data_dict["category"],
            data_dict["label"],
            data_dict["value"]
        )
        if not completed_successfully:
            return_data["error"] = 1
            return_data["message"] = "Could not add data point"
    elif msgtype == "set_project_settings":
        pass
    elif msgtype == "set_category_settings":
        pass
    elif msgtype == "set_entry_settings":
        pass
    else:
        print(f"Unsupported type '{msgtype}'")

    return json.dumps(return_data) # TODO use flask.jsonify instead?


@app.route('/register')
def register():
    project_id = uuid.uuid4().hex
    name = str(request.args["name"])

    # Check if project with name already exists
    with connect(DB_FULL_PATH) as conn:
        cursor = conn.cursor()
        sql = 'SELECT name FROM projects WHERE name=?'
        args = (name, )

        cursor.execute(sql, args)
        data = cursor.fetchall()

        if len(data) > 0:
            text = f"Project '{name}' already exists. Choose a different name!"
            print(text)
            return text

    # Create new project
    with connect(DB_FULL_PATH) as conn:
        cursor = conn.cursor()
        sql = 'INSERT INTO projects (id, name) values(?, ?)'
        args = (project_id, name)

        cursor.execute(sql, args)

    print(f"Registered {name} [{project_id}]")
    return project_id

@app.route('/add_data_point')
def add_data_point():
    try:
        projectid = str(request.args["projectid"])
        category = str(request.args["category"])
        label = str(request.args["label"])
        value = float(request.args["value"])
        if project_exists(projectid):
            if _add_data_point(projectid, category, label, value):
                print(f"Added {projectid}/{category}/{label}/{value}")
        else:
            print(f"Project '{projectid}' does not exist")
    except:
        print(f"Could not add data point {projectid}/{category}/{label}/{value}!")

    return ""


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


if __name__ == "__main__":
    initialize_database()

    # Start clean up thread
    clean_up_thread = threading.Thread(target=thread_clean_up_database)
    clean_up_thread.daemon = True
    clean_up_thread.start()

    print(f"REST Server running on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)