import os
import json

# Flask
from flask import Flask, render_template, request, abort
from flask_socketio import SocketIO

# Stats Server
# from generator import get_values_for_label, USE_DELTA_COMPRESSION
from databaseutilities import project_exists, get_project_id_for_name, get_project_list_for_user, get_id_for_user_pw, register_user
import config_loader

import hashlib

# Load configuration
conf = config_loader.load()
general_conf = conf['general']
server_conf = conf['server']
frontend_conf = conf['server']['frontend']
db_conf = conf['server']['database']

HOST = frontend_conf['host']
PORT = frontend_conf['port']
DEBUG = general_conf['debug']
USE_DELTA_COMPRESSION = server_conf['use_delta_compression']

DB_DIR = db_conf['directory']
DB_FILE = os.path.join(DB_DIR, db_conf['file_name'])


# Initialize server
app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['DEBUG'] = DEBUG

socketio = SocketIO(app, async_mode='eventlet')


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
        return render_template("projectview.html", hostname=projectname, projectid=projectid, ws_host=HOST)

    return abort(404)
    # return abort(int(projectid))

# """
@app.route('/serviceworker.js')
def serviceworker():
    return app.send_static_file('serviceworker.js')
# """

@app.route('/post', methods=['POST'])
def post():
    if request.method == 'POST':
        data = request.json
        data_dict = None
        if isinstance(data, str):  # already json-string, coming from python
            data_dict = json.loads(data)
            print(json.dumps(data_dict, indent=4, sort_keys=True))
        elif isinstance(data, dict):  # coming from JavaScript
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


if __name__ == '__main__':
    print(f"Running server on port {PORT}")
    socketio.run(app, host='0.0.0.0', port=PORT)
