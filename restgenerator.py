# DB_FILE = ":memory:"
DB_FILE = "EnergyLogger.db"


# SQLite
from sqlite3 import connect

with connect(DB_FILE) as conn:
    print("DB_FILE created.")

    cursor = conn.cursor()

    cursor.execute('CREATE TABLE IF NOT EXISTS data (category STRING, label STRING, time REAL, value REAL)')
    cursor.execute('CREATE INDEX IF NOT EXISTS category_index ON data (category, label)')

import time
from datetime import datetime

# Flask
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)
app.config['DEBUG'] = True

@app.route('/')
def index():
  return 'Server is working.'

def _add_data_point(category, label, value):
    timestamp = time.time()
    with connect(DB_FILE) as conn:
        cursor = conn.cursor()
        sql = 'INSERT INTO data (time, category, label, value) values(?, ?, ?, ?)'
        args = (timestamp, category, label, value)

        cursor.execute(sql, args)
        return True
    return False

@app.route('/add_data_point')
def add_data_point():
    category = request.args["category"]
    label = request.args["label"]
    value = request.args["value"]

    if _add_data_point(category, label, value):
        return f"Added {value}"

    return "Could not add data point!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7890)