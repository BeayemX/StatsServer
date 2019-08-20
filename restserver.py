from sqlite3 import connect
import configparser
import os
import time
from datetime import datetime

import threading
import uuid


from databaseutilities import project_exists

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

app = Flask(__name__)
app.config['DEBUG'] = DEBUG

def _add_data_point(projectid, category, label, value):
    timestamp = time.time()
    with connect(DB_FULL_PATH) as conn:
        cursor = conn.cursor()
        sql = 'INSERT INTO data (time, projectid, category, label, value) values(?, ?, ?, ?, ?)'
        args = (timestamp, projectid, category, label, value)

        cursor.execute(sql, args)
        return True
    return False


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
        with connect(DB_FULL_PATH) as conn:
            cursor = conn.cursor()
            sql = 'DELETE FROM data WHERE ROWID IN (SELECT ROWID FROM data WHERE time < ?)'
            args = (current_time - MAX_AGE, )
            cursor.execute(sql, args)

        delta_time = time.time() - current_time

        if (DEBUG):
            print("[ Clean Up ]".ljust(16), str(delta_time))

        time.sleep(CLEAN_UP_INTERVAL)


if __name__ == "__main__":
    with connect(DB_FULL_PATH) as conn:
        print(f"Database at: {DB_FULL_PATH}")

        cursor = conn.cursor()

        cursor.execute('CREATE TABLE IF NOT EXISTS data (projectid STRING, category STRING, label STRING, time REAL, value REAL)')
        cursor.execute('CREATE INDEX IF NOT EXISTS category_index ON data (projectid, category, label)')

        # cursor.execute('DROP TABLE projects')
        cursor.execute('CREATE TABLE IF NOT EXISTS projects (id STRING, name STRING)')


    # Start clean up thread
    clean_up_thread = threading.Thread(target=thread_clean_up_database)
    clean_up_thread.daemon = True
    clean_up_thread.start()

    print(f"REST Server running on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)