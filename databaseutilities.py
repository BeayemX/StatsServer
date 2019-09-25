from sqlite3 import connect
import configparser
import os
import uuid


# FIXME duplicate code in server.py (config reader)
import argparse

parser = argparse.ArgumentParser(description="A setting-config file can be specified.")
parser.add_argument("-c", "--conf", help="path to the config file")
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
        sql = 'SELECT userid, projectid FROM projects'
        args = ()
        cursor.execute(sql, args)
        data = cursor.fetchall()

    project_ids = [x[1] for x in data]

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
        sql = 'SELECT userid, projectid FROM projects'
        args = ()
        cursor.execute(sql, args)
        data = cursor.fetchall()

    for entry in data:
        userid = entry[0]
        projectid = entry[1]
        if projectname == projectid:
            return projectid

    return None

def get_project_list_for_user(userid):
    with connect(DB_FILE) as conn:
        cursor = conn.cursor()
        sql = 'SELECT projectid FROM projects WHERE userid=?'
        args = (userid, )
        cursor.execute(sql, args)
        data = cursor.fetchall()

        projectname_list = []
        for project in data:
            projectname_list.append(project[0])
        return projectname_list

    print("No projects found")
    return []

def register_user(username, password):
    if not does_user_exist(username):
    
        with connect(DB_FILE) as conn:
            user_id = uuid.uuid4().hex
            
            cursor = conn.cursor()
            sql = 'INSERT INTO users (id, username, password) values(?, ?, ?)'
            args = (user_id, username, password)
            cursor.execute(sql, args)
            return user_id
    
    return None

def does_user_exist(username):
    with connect(DB_FILE) as conn:
        cursor = conn.cursor()
        sql = 'SELECT username FROM users WHERE username=?'
        args = (username, )
        cursor.execute(sql, args)
        data = cursor.fetchall()
        return len(data) > 0

def get_id_for_user_pw(username, password):
    with connect(DB_FILE) as conn:
        cursor = conn.cursor()
        sql = 'SELECT id, username, password FROM users'
        args = ()
        cursor.execute(sql, args)
        data = cursor.fetchall()

    for entry in data:
        db_id = entry[0]
        db_user = entry[1]
        db_password = entry[2]

        if db_user == username and db_password == password:
            return db_id

    return None

def initialize_database():
    with connect(DB_FILE) as conn:
        print(f"Database at: {DB_FILE}")

        cursor = conn.cursor()

        #cursor.execute('DROP TABLE data')
        #cursor.execute('DROP TABLE projects')

        cursor.execute('CREATE TABLE IF NOT EXISTS data (projectid STRING, category STRING, label STRING, time REAL, value REAL)')
        cursor.execute('CREATE INDEX IF NOT EXISTS category_index ON data (projectid, category, label)')

        cursor.execute('CREATE TABLE IF NOT EXISTS projects (userid STRING, projectid STRING)')
        cursor.execute('CREATE TABLE IF NOT EXISTS users (id STRING, username STRING, password STRING)')
