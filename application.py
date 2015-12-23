from flask import g, Flask, render_template, request, redirect, url_for, \
                  jsonify, flash
from functools import wraps
from sqlalchemy import create_engine, DateTime
from sqlalchemy.orm import sessionmaker
from dbcatalog_setup5 import Base, Category, Item, User
from flask import session as login_session
import random
import string
import datetime
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog Menu Application"


engine = create_engine('postgresql://catalog:catalog@localhost:5432/catalog')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


# Method to login using google+ credentials
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    print("form state" + request.args.get('state'))
    print("login state" + login_session['state'])
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already \
		                         connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # Check if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
    print("here")
    print(login_session['user_id'])

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px; \
	                       -webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    return output


# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect', methods=['POST'])
def gdisconnect():
    # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        # Reset the user's sesson.
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Method to output catalog data in json format
@app.route('/catalog.JSON')
def catalogJSON():
    categories = session.query(Category).all()
    serializedCategories = []
    for i in categories:
        new_cat = i.serialize
        items = session.query(Item).filter_by(category_id=i.id).all()
        serializedItems = []
        for j in items:
            serializedItems.append(j.serialize)
        new_cat['items'] = serializedItems
        serializedCategories.append(new_cat)
    return jsonify(categories=[serializedCategories])


# Method to show the landing page of the application
@app.route('/')
@app.route('/categories')
def showCategories():
    categories = session.query(Category).all()
    # Getting the datetime 5 days before to show the items added in past 5 days
    today = datetime.datetime.today()
    sub_day = datetime.timedelta(days=5)
    earliest = today - sub_day
    items = session.query(Item).all()
    latestitems = []
    for i in items:
        if i.created_date > earliest:
            latestitems.append(i)
    if 'username' not in login_session:
        state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        login_session['state'] = state
        return render_template('publiccategories.html', categories=categories,\
                                items=latestitems, STATE=state)
    else:
	    return render_template('categories.html', categories=categories, \
		                        items=latestitems)


# Method to show the items in category
@app.route('/catalog/<string:category_name>/items')
def showItems(category_name):
    category = session.query(Category).filter_by(name=category_name).one()
    categories = session.query(Category).all()
    items = session.query(Item).filter_by(category_id=category.id)
    rows = session.query(Item).filter_by(category_id=category.id).count()
    if 'username' not in login_session:
        state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        login_session['state'] = state
        return render_template('publicShowItems.html', \
		                        category_name=category.name, \
								categories=categories, items=items, rows=rows,\
								STATE=state)
    else:
	    return render_template('showItems.html', category_name=category.name, \
		                        categories=categories, items=items, rows=rows)


# Method to show description of a item  
@app.route('/catalog/<string:category_name>/<string:item_title>')
def showItemDescription(category_name, item_title):
    item = session.query(Item).filter_by(title=item_title).one()
    if 'username' not in login_session:
        state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        login_session['state'] = state
        return render_template('publicShowItemDescription.html', item=item, \
		                        STATE=state)
    else:
        if item.user_id != login_session['user_id']:
            return render_template('loggedShowItemDescription.html', item=item)
        else:
            return render_template('showItemDescription.html', item=item)


# Method to add item
@app.route('/catalog/add', methods=['GET', 'POST'])
def addItem():
    categories = session.query(Category).all()
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))

    if request.method == 'POST':
        newItem = Item(title=request.form['title'], description=request.form[
                           'description'], category_id=request.form['category'],
						   user_id=login_session['user_id'])
        count=session.query(Item).filter_by(title=newItem.title).count()
        if count > 0:
            flash("Item already exists. Please select a different title")
            return render_template('addItem.html', categories=categories)
        else:
            session.add(newItem)
            session.commit()
            return redirect(url_for('showCategories'))
    else:
        return render_template('addItem.html', categories=categories)


# Method to edit item
@app.route('/catalog/<string:item_title>/edit', methods=['GET', 'POST'])
def editItem(item_title):
    categories = session.query(Category).all()
    editedItem = session.query(Item).filter_by(title=item_title).one()
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))
    
    if request.method == 'POST':
        count=session.query(Item).filter_by(title=request.form['title']).count()
        if count > 0:
            flash("Item already exists. Please select a different title")
            return render_template('editItem.html', item=editedItem, \
		                        categories=categories)
        if request.form['title']:
            editedItem.title = request.form['title']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['category']:
            editedItem.category_id = request.form['category']
        session.add(editedItem)
        session.commit()
        return redirect(url_for('showCategories'))
    else:
        return render_template('editItem.html', item=editedItem, \
		                        categories=categories)


# Method to delete item
@app.route('/catalog/<string:item_title>/delete', methods=['GET', 'POST'])
def deleteItem(item_title):
    deleteItem = session.query(Item).filter_by(title=item_title).one()
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))

    if request.method == 'POST':
        session.delete(deleteItem)
        session.commit()
        return redirect(url_for('showCategories'))
    else:
        return render_template('deleteItem.html', item=deleteItem)


# Method to create user
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


# Method to get user info
def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


# Method to get user id
def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in login_session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


if __name__ == '__main__':
    app.debug = True
    app.secret_key = 'fHNMjRocwJdTTRJzmXajYLfK'
    app.config['SESSION_TYPE'] = 'filesystem'
    app.run(host='0.0.0.0', port=5000)
