
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
  # accessible as a variable in index.html:
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import text
from flask import Flask, request, render_template, g, redirect, Response, session, url_for, flash
from flask_restful import Resource, Api
from datetime import datetime
import random

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.jinja_env.filters['zip'] = zip
app.config['SECRET_KEY'] = os.urandom(24)
api = Api(app)


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
# engine.execute("""CREATE TABLE IF NOT EXISTS test (
#   id serial,
#   name text
# );""")
# engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")
# class All_Store(Resource):
#     def get(self):
#       cursor = g.conn.execute("SELECT name FROM store")
#       names = []
#       for result in cursor:
#         print(result[0])
#         names.append(result[0])  # can also be accessed using result[0]
#       cursor.close()
#       context = dict(data = names)
#       return render_template("store.html", **context)

# api.add_resource(All_Store, '/store')

@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request.

  The variable g is globally accessible.
  """
  if not session.get('uid') and request.endpoint!='index' and request.endpoint != 'main_page':
      print(request.endpoint)
      return redirect('/')
  try:
    g.conn = engine.connect()
    print(g.conn)
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



@app.route('/')
def index():
  return render_template("index.html")

@app.route('/club')
def all_clubs():
    cursor = g.conn.execute("SELECT C.name, A.club_id, COUNT(*) FROM club C NATURAL JOIN attend A GROUP BY C.name, A.club_id ORDER BY COUNT(*) DESC" )
    club_name = []
    club_id = []
    club_amount = []
    for result in cursor:
      club_name.append(result[0]) 
      club_id.append(result[1])
      club_amount.append(result[2])
    cursor = g.conn.execute("SELECT U.name, L.club_id FROM users U NATURAL JOIN leads L")
    leader_name = []
    for result in cursor:
      leader_name.append(result[0])
    cursor.close()
    context = dict(club_name = club_name, club_id=club_id, club_amount=club_amount, leader_name=leader_name )
    return render_template("club.html", **context)

@app.route('/club/<club_id>')
def individual_club(club_id):
  #Get club members
  cursor = g.conn.execute("SELECT U.name, A.user_id FROM attend A NATURAL JOIN users U WHERE A.club_id = %(club_id)s", {"club_id":club_id})
  member_names = []
  club_members = []
  for result in cursor:
    member_names.append(result[0])
    club_members.append(result[1]) 
  #Get club name
  cursor = g.conn.execute("SELECT C.name FROM club C WHERE C.club_id = %(club_id)s", {"club_id":club_id})
  club_name = []
  for result in cursor:
    club_name.append(result[0])
  
  
  #Get club tasks
  cursor = g.conn.execute("SELECT D.task_id, D.start_time, D.finish_time FROM do_club_tasks D WHERE D.club_id = %(club_id)s", {"club_id":club_id})
  past_tasks = []
  for result in cursor:
    past_tasks.append(result)
  
  context = dict(member_names=member_names, club_members=club_members, club_name=club_name, past_tasks=past_tasks)
  cursor.close()
  
  return render_template("club_individual.html", **context)
    

@app.route('/club/management')
def club_lead():
  cursor = g.conn.execute("SELECT C.name, L.club_id FROM leads L Natural Join club C WHERE L.user_id = %(user_id)s", {"user_id":session['uid']})
  club_names = []
  club_ids = []
  for result in cursor:
    club_names.append(result[0])
    club_ids.append(result[1]) 
  context = dict(club_names=club_names, club_ids=club_ids)
  cursor.close()
  return render_template("club_management.html", **context)

@app.route('/club/management/<club_id>/user', methods=['GET', 'POST'])
def manage_club_user(club_id):
    if not session.get('manage_club'):
      session['manage_club'] = club_id
    if request.method == 'GET':
      cursor = g.conn.execute("SELECT U.name, A.user_id FROM attend A NATURAL JOIN users U WHERE A.club_id = %(club_id)s", {"club_id":club_id})
      member_names = []
      user_ids = []
      for result in cursor:
        member_names.append(result[0])
        user_ids.append(result[1]) 
      cursor = g.conn.execute("SELECT C.name FROM club C WHERE C.club_id = %(club_id)s", {"club_id":club_id})
      club_name = []
      for result in cursor:
        club_name.append(result[0])
      context = dict(member_names=member_names, user_ids=user_ids, club_id=club_id, club_name=club_name)
      cursor.close()
      return render_template("club_management_user.html", **context)
    elif request.method == 'POST':
      g.conn.execute("INSERT INTO attend(user_id, club_id) VALUES (%(user_id)s, %(club_id)s)", {'user_id': request.form['uid'], 'club_id': club_id} )
      return redirect(url_for('manage_club_user', club_id=club_id))

@app.route('/club/<club_id>/<club_task_id>')
def find_club_task_info(club_id, club_task_id):
  cursor = g.conn.execute("SELECT CT.difficulty, CT.reward, CT.experience, CT.min_peoplel_limit, D.start_time, D.finish_time FROM do_club_tasks D NATURAL JOIN club_task CT WHERE D.club_id = %(club_id)s AND D.task_id = %(club_task_id)s ", {"club_id":club_id, "club_task_id":club_task_id})
  club_task_detail = []
  for result in cursor:
    club_task_detail.append(result)
  context = dict(club_task_detail=club_task_detail, club_id=club_id, club_task_id=club_task_id)
  cursor.close()
  return render_template("club_task_detail_finish.html", **context)
  


@app.route('/club/management/<club_id>/user/<user_id>')
def delete_user(club_id, user_id):
  g.conn.execute("DELETE FROM attend A WHERE A.club_id = %(club_id)s AND A.user_id = %(user_id)s", {"club_id":club_id, "user_id":user_id})
  
  return redirect(url_for('manage_club_user', club_id=club_id))
  
@app.route('/club/management/<club_id>/club_task')
def manage_club_task(club_id):
    if not session.get('manage_club'):
      session['manage_club'] = club_id
    cursor = g.conn.execute("SELECT D.task_id FROM do_club_tasks D WHERE D.club_id = %(club_id)s", {"club_id":club_id})
    completed_club_task = []
    for result in cursor:
      completed_club_task.append(result[0]) 
    context = dict(completed_club_task =completed_club_task, club_id=club_id)
    return render_template("club_task_finish.html", **context)

@app.route('/club_tasks')
def all_club_tasks():
  cursor = g.conn.execute("SELECT * FROM club_task C LIMIT 100")
  club_task_detail = []
  for result in cursor:
    club_task_detail.append(result)
  context = dict(club_task_detail=club_task_detail, club_id=session['manage_club'])
  return render_template("club_tasks.html", **context)

@app.route('/club_tasks/add/<club_task_id>')
def add_club_tasks(club_task_id):
  try:
    g.conn.execute("INSERT INTO do_club_tasks(task_id, club_id, start_time) VALUES (%(task_id)s, %(club_id)s, %(start_time)s)", {'task_id': club_task_id, 'club_id': session['manage_club'], 'start_time': datetime.utcnow()} )
    flash('You have successfully added the club task!')
    return redirect(url_for('all_club_tasks'))
  except:
    flash('Something went wrong (Are you a leader who manages club tasks?)')
    return redirect(url_for('all_club_tasks'))
      

@app.route('/my_club')
def my_club():
  cursor = g.conn.execute("SELECT C.name, A.club_id FROM club C NATURAL JOIN attend A WHERE A.user_id = %(user_id)s", {'user_id': session['uid']})
  clubs = []
  club_ids = []
  for result in cursor:
        clubs.append(result[0])
        club_ids.append(result[1])
  cursor.close()
  context = dict(clubs=clubs, club_ids=club_ids)
  return render_template("my_club.html", **context)
      


@app.route('/store')
def get_store():
      cursor = g.conn.execute("SELECT address FROM store")
      names = []
      for result in cursor:
        #print(result[0])
        names.append(result[0])  # can also be accessed using result[0]
      cursor.close()
      context = dict(data = names)
      return render_template("store.html", **context)

@app.route('/main/items')
def user_items():
    cursor = g.conn.execute("SELECT I.name FROM own O Natural Join item I WHERE O.user_id = %(user_id)s", {'user_id': session['uid']} )
    users_item = []
    for result in cursor:
      #print(result[0])
      users_item.append(result[0])  # can also be accessed using result[0]
    cursor.close()
    context = dict(users_item = users_item)
    return render_template("user_item.html", **context)

      

@app.route('/add_item/<item_id>', methods=['GET','POST'])
def add_item(item_id):
    if request.method == 'GET':
      return 'add item function waiting...'
    elif request.method == 'POST':
      try:
        g.conn.execute("INSERT INTO own(user_id, product_id, date) VALUES (%(user_id)s, %(item_id)s, %(date)s)", {'user_id': int(session['uid']), 'item_id': item_id, 'date': datetime.today().strftime('%Y-%m-%d')} )
      except:
        return "You already have this item!!!"
      return redirect('/main/items')
    else:
      return "Method unknown"

@app.route('/store/<store_addr>')
def get_store_by_id(store_addr):
      if not session.get('store_addr'):
            session['store_addr'] = store_addr
      print("hhhhhhhhhh", session['store_addr'])
      cursor = g.conn.execute("SELECT S.address, I.name, I.product_id FROM store S Natural Join have H, item I WHERE S.address =  %(store_addr)s LIMIT 100", {'store_addr': store_addr} )
      random_sample = random.sample(range(1, 100), 10)
      
      store_addresses = []
      item_names = []
      item_ids = []
      for result in cursor:
        #print(result)
        store_addresses.append(result[0])
        item_names.append(result[1])
        item_ids.append(result[2])
      cursor.close()
      context = dict(store_addresses = store_addresses, item_names=item_names, item_ids=item_ids, random_sample=random_sample, store_addr=session['store_addr'])
      return render_template("store_individual.html", **context)
      
      


@app.route('/another')
def another():
  return render_template("index.html")


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

@app.route('/profile')
def profile():
    user_id = session.get('uid')
    cur = g.conn.execute('SELECT * FROM sc4926.users WHERE user_id = {}'.format(user_id))
    user_info = dict(cur.fetchone())
    params = {'user_info': user_info}
    cur.close()
    return render_template("profile.html", **user_info)


if __name__ == "__main__":
      app.run(host='0.0.0.0', debug=True, port=8111)
  # import click

  # @click.command()
  # @click.option('--debug', is_flag=True)
  # @click.option('--threaded', is_flag=True)
  # @click.argument('HOST', default='0.0.0.0')
  # @click.argument('PORT', default=8111, type=int)
  # def run(debug, threaded, host, port):
  #   """
  #   This function handles command line parameters.
  #   Run the server using:

  #       python3 server.py

  #   Show the help text using:

  #       python3 server.py --help

  #   """

  #   HOST, PORT = host, port
  #   print("running on %s:%d" % (HOST, PORT))
  #   app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

  # run()
