from flask import Flask
from flask import request
from flask import g
import sqlite3
import os
import re
import datetime
from collections import namedtuple

DATABASE = 'ciproxy.db'
FIELDS = """commitid TEXT, branch TEXT, backend TEXT,
            machine TEXT, make_result INT, cmake_result INT, ctest_result INT,
            logfile TEXT, [timestamp] TIMESTAMP"""
NTFIELDS = re.sub(r'[A-Z\[\]]', '', FIELDS)

BuildResult = namedtuple('BuildResult', NTFIELDS)

app = Flask(__name__)

def _db_setup():
    # Create file if it does not exist.
    if not os.path.isfile(DATABASE):
        with open(DATABASE, 'x') as f:
            pass

    # Connect and create table if it does not exist.
    db = g._database = sqlite3.connect(DATABASE)

    create = "CREATE TABLE IF NOT EXISTS results (id INTEGER PRIMARY KEY, " + \
                FIELDS + "creation DATE);"
    db.cursor().executescript(create)
    db.commit()
    return db


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = _db_setup()
    return db

def _db_add_result(result):
    db = get_db()
    db.execute("INSERT INTO results(" + NTFIELDS + ") VALUES(" +
            ','.join(['?'] * (NTFIELDS.count(',')+1)) + ")", result)
    db.commit()

def _db_get_branch(branch):
    db = get_db()
    c = db.execute("""SELECT make_result, cmake_result, ctest_result
                  FROM results
                  WHERE branch=? ORDER BY timestamp DESC LIMIT 1;""",
                [branch])
    return c.fetchall()


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route("/newbr", methods=['POST','PUT'])
def newbr():
    result = BuildResult(
            request.args['commitid'],
            branch = request.args['branch'],
            backend = request.args['backend'],
            machine = request.args['machine'],
            make_result = request.args['make_result'],
            cmake_result = request.args['cmake_result'],
            ctest_result = request.args['ctest_result'],
            logfile = 'log',
            timestamp=datetime.datetime.now())
    _db_add_result(result)
    return "Success"

@app.route("/getbr", methods=['GET'])
def getbr():
    return str(_db_get_branch(request.args['branch']))
