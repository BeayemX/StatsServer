import os
import time
import uuid

from sqlite3 import connect

import config_loader

# Load configuration
conf = config_loader.load()
general_conf = conf['general']
db_conf = conf['server']['database']


DB_DIR = db_conf['directory']
DB_FILE = os.path.join(DB_DIR, db_conf['file_name'])

DEBUG_LOG = general_conf['log']


def project_exists(projectid):
    with connect(DB_FILE) as conn:
        cursor = conn.cursor()
        sql = 'SELECT userid, projectid FROM projects'
        args = ()
        cursor.execute(sql, args)
        data = cursor.fetchall()

    project_ids = [x[1] for x in data]

    if DEBUG_LOG:
        # print("Available projects:")
        for entry in data:
            userid = entry[0]
            projectname = entry[1]
            # print(" ", userid, projectname)

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


def add_data_point(userid, projectid, category, label, value):
    timestamp = time.time()
    with connect(DB_FILE) as conn:
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


def initialize_database():
    with connect(DB_FILE) as conn:
        print(f"Database at: {DB_FILE}")

        cursor = conn.cursor()

        #cursor.execute('DROP TABLE data')
        #cursor.execute('DROP TABLE projects')

        cursor.execute('CREATE TABLE IF NOT EXISTS data (userid STRING, projectid STRING, category STRING, label STRING, time REAL, value REAL)')
        cursor.execute('CREATE INDEX IF NOT EXISTS category_index ON data (userid, projectid, category, label)')

        cursor.execute('CREATE TABLE IF NOT EXISTS projects (userid STRING, projectid STRING)')
        cursor.execute('CREATE TABLE IF NOT EXISTS users (id STRING, username STRING, password STRING)')


def delete_data_keep_users():
    with connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('DROP TABLE data')
        cursor.execute('DROP TABLE projects')
        print("Data has been deleted")
    initialize_database()


if __name__ == "__main__":
    if input("Delete data (keeping users)?\n> ") == 'yes':
        delete_data_keep_users()
    else:
        print("Aborted...")
