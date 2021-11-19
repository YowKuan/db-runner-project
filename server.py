
"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver
To run locally:
    python3 server.py
Go to http://localhost:8111 in your browser.
A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""
import os
import json
  # accessible as a variable in index.html:
from collections import defaultdict
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, session
import datetime

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.config['SECRET_KEY'] = os.urandom(24)

#
# The following is a dummy URI that does not connect to a valid database. You will need to modify it to connect to your Part 2 database in order to use the data.
#
# XXX: The URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@34.74.246.148/proj1part2
#
# For example, if you had username gravano and password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://gravano:foobar@34.74.246.148/proj1part2"
#
DATABASEURI = "postgresql://sc4926:8023@34.74.246.148/proj1part2"


#
# This line creates a database engine that knows how to connect to the URI above.
#
engine = create_engine(DATABASEURI)

#
# Example of running queries in your database
# Note that this will probably not work if you already have a table named 'test' in your database, containing meaningful data. This is only an example showing you how to run queries in your database using SQLAlchemy.
#
engine.execute("""CREATE TABLE IF NOT EXISTS test (
  id serial,
  name text
);""")
engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")


@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request.

  The variable g is globally accessible.
  """
  try:
    g.conn = engine.connect()
  except:
    print("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't, the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to, for example, localhost:8111/foobar/ with POST or GET then you could use:
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: https://flask.palletsprojects.com/en/2.0.x/quickstart/?highlight=routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
@app.route('/')
def index():
  session['uid'] = False
  return render_template("index.html")

@app.route('/another')
def another():
  return render_template("another.html")


# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
  name = request.form['name']
  g.conn.execute('INSERT INTO test(name) VALUES (%s)', name)
  return redirect('/')


@app.route('/login')
def login():
    abort(401)
    this_is_never_executed()

@app.route('/main', methods=['POST', 'GET'])
def main_page():
    if request.method == 'POST':
        user_id = request.form['uid']
        session['uid'] = user_id
    else:
        user_id = session.get('uid')
    cur = g.conn.execute("SELECT name FROM sc4926.users WHERE user_id = %(user_id)s", {'user_id': user_id})
    user_info = dict(cur.fetchone())
    cur.close()
    user_info['first_name'] = user_info['name'].split()[0]
    return render_template("main.html", **user_info)

@app.route('/run')
def run():
    user_id = session.get('uid')
    cur = g.conn.execute("SELECT run_id, distance, start_time, time_spent \
        FROM sc4926.run_exercise WHERE user_id = %(user_id)s", {'user_id': user_id})
    run_raw_data = list(cur.fetchall())
    run_new_data = []
    for i, row in enumerate(run_raw_data):
        run_new_data.append({})
        for k, v in row.items():
            if k == 'distance':
                run_new_data[i]['Distance'] = str(round(v / 1.6, 2)) + ' mile'
            elif k == 'start_time':
                run_new_data[i]['Date'] = '/'.join([str(v.year), str(v.month), str(v.day)])
            elif k == 'time_spent':
                run_new_data[i]['Time'] = str(datetime.timedelta(seconds=int(v)))
            else:
                run_new_data[i]['Id'] = v

    cur.close()
    return render_template("run.html", run_stats=run_new_data)

@app.route('/run/<run_id>')
def run_detail(run_id):
    user_id = session.get('uid')
    cur = g.conn.execute('SELECT * FROM sc4926.run_exercise WHERE user_id = %(user_id)s \
       AND run_id = %(run_id)s', {'user_id': user_id, 'run_id': run_id})
    run_raw_data = dict(cur.fetchone())
    run_raw_data['time_spent'] = str(datetime.timedelta(seconds=int(run_raw_data['time_spent'])))
    run_raw_data['distance'] = str(round(run_raw_data['distance'] / 1.6, 4)) + ' mile'
    run_raw_data['heart_rate'] = str(round(run_raw_data['heart_rate'], 7) * 10)
    run_raw_data['elevation'] = str(round(run_raw_data['elevation'], 6))
    run_raw_data['calories'] = str(round(run_raw_data['calories'], 6))
    cur.close()

    cur = g.conn.execute('SELECT * FROM sc4926.run_detailed_km \
        WHERE run_id = %(run_id)s', {'run_id': run_id})
    run_mile_raw_data = list(cur.fetchall())
    run_mile = []
    for i, row in enumerate(run_mile_raw_data):
        run_mile.append({})
        for k, v in row.items():
            if k == 'time_spent':
                run_mile[i]['time_spent'] = str(datetime.timedelta(seconds=int(v)))
            elif k == 'pace':
                run_mile[i]['pace'] = str(round(v, 6))
            else:
                run_mile[i][k] = v

    return render_template("run_detailed.html", run_detail_stats=run_raw_data, run_mile_stats=run_mile)

@app.route('/profile/<user_id>')
def check_profile(user_id):
    cur = g.conn.execute('SELECT * FROM sc4926.users WHERE user_id = {}'.format(user_id))
    user_info = dict(cur.fetchone())
    cur.close()
    return render_template("profile.html", user_info=user_info)

@app.route('/profile')
def profile():
    user_id = session.get('uid')
    cur = g.conn.execute('SELECT * FROM sc4926.users WHERE user_id = {}'.format(user_id))
    user_info = dict(cur.fetchone())
    cur.close()
    return render_template("profile.html", user_info=user_info)

@app.route('/leaderboard')
def leaderboard():
    return render_template("leaderboard.html")

@app.route('/leaderboard/distance')
def distance_ranking():
    cur = g.conn.execute('SELECT user_id, SUM(distance) as total_distance FROM sc4926.run_exercise \
      GROUP BY (user_id) ORDER BY (SUM(distance)) DESC LIMIT 100')
    ranking = list(cur.fetchall())
    return render_template("ranking.html", ranking=ranking, type='Total Distance')

@app.route('/leaderboard/speed')
def speed_ranking():
    cur = g.conn.execute('SELECT user_id, SUM(distance) / SUM(time_spent) as avg_speed \
        FROM sc4926.run_exercise GROUP BY (user_id) ORDER BY (avg_speed) DESC LIMIT 100;')
    ranking = list(cur.fetchall())
    return render_template("ranking.html", ranking=ranking, type='Average Speed')


@app.route('/task')
def task():
    return render_template("task.html")

@app.route('/complete_task/<task_id>', methods=['POST', 'GET'])
def task_detail(task_id):
    user_id = session.get('uid')
    if request.method == 'POST':
        # Check if the task has done
        columns = ""
        cur = g.conn.execute('SELECT * FROM sc4926.do_tasks WHERE user_id = %(user_id)s \
          AND task_id = %(task_id)s', {'user_id': user_id, 'task_id': task_id})
        user_task_info = list(cur.fetchall())
        cur.close()
        if len(user_task_info) > 0:
            return render_template("error_task.html", err_mesage='The task has already been done!')
        
        # Check the expereince level
        cur = g.conn.execute('SELECT * FROM sc4926.users WHERE user_id = {}'.format(user_id))
        user_info = dict(cur.fetchone())
        cur.close()
        cur = g.conn.execute('SELECT * FROM sc4926.individual_task WHERE task_id = %(task_id)s', {'task_id': task_id})
        task_info = dict(cur.fetchone())
        cur.close()
        if user_info['level'] < task_info['level_limit']:
            return render_template("error_task.html", err_mesage='Your level can not do this task!')

        # Insert new task
        start_time = finish_time = "'" + datetime.datetime.now().strftime(format="%Y-%m-%d %H:%M:%S") + "'"
        value = ','.join([user_id, task_id, start_time, finish_time])
        cur = g.conn.execute('INSERT INTO do_tasks (user_id, task_id, start_time, finish_time)\
          Values ({});'.format(value))
        
        # Update user profile
        updated_experience = user_info['experience'] + task_info['experience']
        updated_coins = user_info['coin'] + task_info['reward']
        cur = g.conn.execute('UPDATE sc4926.users SET experience = %(exp)s, \
            coin = %(coin)s WHERE user_id = %(uid)s', {'exp': updated_experience, 'coin': updated_coins, 'uid': user_id})
        cur.close()


    cur = g.conn.execute('SELECT * FROM sc4926.do_tasks WHERE user_id = %(user_id)s \
       AND task_id = %(task_id)s', {'user_id': user_id, 'task_id': task_id})
    user_task_info = dict(cur.fetchone())
    cur.close()
    cur = g.conn.execute('SELECT * FROM sc4926.individual_task WHERE task_id = %(task_id)s', {'task_id': task_id})
    task_info = dict(cur.fetchone())
    cur.close()
    return render_template("individual_task_detailed.html", do_task_info=user_task_info, task_info=task_info)

@app.route('/all_task')
def all_task():
    cur = g.conn.execute("SELECT * FROM sc4926.individual_task")
    task_data = list(cur.fetchall())
    return render_template("all_task.html", task_info=task_data)

@app.route('/complete_task')
def complete_task():
    user_id = session.get('uid')
    cur = g.conn.execute("SELECT * FROM sc4926.do_tasks WHERE user_id = %(user_id)s", {'user_id': user_id})
    task_raw_data = list(cur.fetchall())
    cur.close()
    task_new_data = []
    task_id = None
    for i, row in enumerate(task_raw_data):
        task_new_data.append({})
        for k, v in row.items():
            if k == 'finish_time':
                task_new_data[i]['Finish Date'] = '/'.join([str(v.year), str(v.month), str(v.day)])
            elif k == 'task_id':
                task_new_data[i]['Task_ID'] = v
                task_id = v
        if task_id:
            cur = g.conn.execute('SELECT * FROM sc4926.individual_task WHERE task_id = %(task_id)s', {'task_id': task_id})
            task_info = dict(cur.fetchone())
            cur.close()
            task_new_data[i]['Difficulty'] = task_info['difficulty']
    return render_template("individual_task.html", task_info=task_new_data)

if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using:

        python3 server.py

    Show the help text using:

        python3 server.py --help

    """

    HOST, PORT = host, port
    print("running on %s:%d" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

  run()
