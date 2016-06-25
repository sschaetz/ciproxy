from flask import Flask
from flask import request
from flask import g
import sqlite3
import os
import re
import datetime
from collections import namedtuple

TEMPLATE = 'badge_template.svg'
DATABASE = 'ciproxy.db'
FIELDS = """commitid TEXT, branch TEXT, backend TEXT,
            machine TEXT, make_result INT, cmake_result INT, ctest_result INT,
            logfile TEXT, [timestamp] TIMESTAMP"""
NTFIELDS = re.sub(r'[A-Z\[\]]', '', FIELDS)

BuildResult = namedtuple('BuildResult', NTFIELDS)

TemplateColors = dict(CUDA='#ff7878', OPENCL='#78ff78', METAL='#007878')
GreenColor = '#00b900'
RedColor = '#b9001e'

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

def _get_badge_template():
    tmp = getattr(g, '_template', None)
    if tmp is None:
        with open(TEMPLATE, 'r') as f:
            g._template = f.read()
    return g._template

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

def _db_get_latest_branch_result(branch):
    db = get_db()
    c = db.execute("""SELECT make_result, cmake_result, ctest_result, backend
                  FROM results
                  WHERE branch=? ORDER BY timestamp DESC LIMIT 3;""",
                [branch])
    return c.fetchall()

def _compute_result(result_interm):
    print(result_interm)
    result = dict()
    for r in result_interm:
        result[r[3]] = not sum([int(x) for x in r[0:3]])
    return result

def _make_badge(result):
    pass

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

    badge = _get_badge_template()
    result = _compute_result(
            _db_get_latest_branch_result(request.args['branch']))

    for k, v in TemplateColors.items():
        print(k, v, RedColor if not result[k] else GreenColor)
        badge = badge.replace(v,
                RedColor if not result[k] else GreenColor)

    return badge
