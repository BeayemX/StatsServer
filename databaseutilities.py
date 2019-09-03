from sqlite3 import connect
import configparser
import os


# FIXME duplicate code in server.py (config reader)
import argparse

parser = argparse.ArgumentParser(description="This will show all values that can be toggled. The initial value is gathered from the configuration file(s). The default values are used if there are no files provided.")
parser.add_argument("-c", "--conf", help="toggle the tasks category")
args = parser.parse_args()

conf_path = "settings.conf"
if args.conf and os.path.isfile(args.conf):
    conf_path = args.conf

# FIXME duplicate code in server.py (database connection)
# Load settings from config file
conf = configparser.ConfigParser()
conf.read(os.path.join(os.path.dirname(__file__), conf_path))

DB_DIR = conf["Generator"]["DatabaseDirectory"]
DB_FILE = os.path.join(DB_DIR, conf["Generator"]["DatabaseName"])

DEBUG = conf["Server"].getboolean("Debug")

def project_exists(projectid):
    with connect(DB_FILE) as conn:
        cursor = conn.cursor()
        sql = 'SELECT id, name FROM projects'
        args = ()
        cursor.execute(sql, args)
        data = cursor.fetchall()

    project_ids = [x[0] for x in data]

    if DEBUG:
        print("Available project IDs:")
        for entry in data:
            project_id = entry[0]
            name = entry[1]
            print(" ", project_id, name)

    return projectid in project_ids

def get_project_id_for_name(projectname):

    with connect(DB_FILE) as conn:
        cursor = conn.cursor()
        sql = 'SELECT id, name FROM projects'
        args = ()
        cursor.execute(sql, args)
        data = cursor.fetchall()

    for entry in data:
        id = entry[0]
        name = entry[1]
        if name == projectname:
            return id

    return None

def get_project_list_for_user(userid):
    with connect(DB_FILE) as conn:
        cursor = conn.cursor()
        sql = 'SELECT id, name FROM projects'
        args = ()
        cursor.execute(sql, args)
        data = cursor.fetchall()

        data_dict = {}

        for entry in data:
            id = entry[0]
            name = entry[1]
            data_dict[id] = {
                "name": name
            }

        return data_dict

    print("No projects found")
    return None