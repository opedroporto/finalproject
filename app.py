from helpers import fit, is_url_image
from flask import Flask, render_template, request, session, redirect, jsonify, flash, url_for
from flask_session import Session
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from tempfile import mkdtemp
from sqlite3 import connect
from werkzeug.security import check_password_hash, generate_password_hash
from http import HTTPStatus
from apiclient.discovery import build
import requests
import time
import os
from dotenv import load_dotenv

project_folder = os.path.expanduser('/home/bearing/project')
load_dotenv(os.path.join(project_folder, '.env'))

app = Flask(__name__)

# reload templates automatically (no need to restart flask app)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['STATIC_AUTO_RELOAD'] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

Session(app)


# Configure Mail to send reset password links
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get('mail-sender')
app.config["MAIL_PASSWORD"] = os.environ.get('mail-password')
app.config["MAIL_PORT"] = 587
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get('mail-sender')
mail = Mail(app)

# confirmation token
serializer = URLSafeTimedSerializer(os.environ.get('secret-key'))
user_by_token = {}

#global users: all users
users = ()
# global cards: stores all user's cards
cards = ()
# global examples: stores all user's examples
examples = ()

# database
db = connect('/home/bearing/project/bearing.db', check_same_thread=False)
db_cursor = db.cursor()


# redirect to HTTPS
@app.before_request
def before_request():
    if not request.is_secure:
        url = request.url.replace('http://', 'https://', 1)
        code = 301
        return redirect(url, code=code)



# login
start_login = time.time()
black_list_login = []

@app.route('/login', methods=['GET', 'POST'])
def login():

    # method POST
    if request.method == 'POST':

        # BLACK LIST
        global black_list_login, start_login
        ip = request.remote_addr

        # unblacklist ip
        if time.time() - start_login > 5:
            try:
                black_list_login.remove(ip)
            except:
                pass

        # return message if ip blacklisted
        if ip in black_list_login:
            start_login = time.time()
            return render_template('login.html', message='Wait 5 seconds!')

        # blacklist ip
        black_list_login.append(ip)
        start_login = time.time()

        # SANITIZE ERRORS

        # no username
        if not request.form.get('username'):
            return render_template('login.html', message='Username missing!')

        # no password
        if not request.form.get('password'):
            return render_template('login.html', message='Password missing!')

        # username does not exist
        db_cursor.execute("SELECT * FROM users WHERE username = (?)",
        [request.form.get('username')]
        )
        user = db_cursor.fetchall()
        if len(user) != 1:
            return render_template('login.html', message='Invalid username and/or password!')
        session['user'] = user[0]

        # password does not match username
        if not check_password_hash(session['user'][2], request.form.get('password')):
            return render_template('login.html', message='Invalid username and/or password!')



        # IF SUCCESFUL
        session['user_id'] = session['user'][0]


        # if not mail registered
        db_cursor.execute('SELECT mail FROM users WHERE id = (?)',
        [session['user_id']]
        )
        mail = db_cursor.fetchone()[0]

        if not mail:
            flash('We recommend you to add an e-mail to your account. Otherwise you will not be able to recover your account if you forget your password.')

        return redirect('/')

    # method GET
    else:
        return render_template('login.html')


# add mail
@app.route('/add_mail', methods=['POST'])
def add_mail():

    # SANITIZE ERRORS

    # no mail
    if not request.form.get('mail'):
        flash('We recommend you to add an e-mail to your account. Otherwise you will not be able to recover your account if you forget your password.')
        flash('E-mail missing!')
        return redirect('/')

    mail = request.form.get('mail')

    # wrong mail format
    if not '@' in mail or not '.' in mail or 3 > len(mail) or len(mail) > 64:
        flash('We recommend you to add an e-mail to your account. Otherwise you will not be able to recover your account if you forget your password.')
        flash('E-mail not allowed!')
        return redirect('/')

    # IF SUCCESFUL
    db_cursor.execute('UPDATE users SET mail = (?) WHERE id = (?)',
    [mail,
    session['user_id']]
    )
    db.commit()

    # select all users
    global users
    db_cursor.execute('SELECT * FROM users')
    users = db_cursor.fetchall()

    return redirect('/')


# register
start_register = time.time()
black_list_register = []

@app.route('/register', methods=['GET','POST'])
def register():

    # method POST
    if request.method == "POST":

         # BLACK LIST
        global black_list_register, start_register
        ip = request.remote_addr

        # unblacklist ip
        if time.time() - start_register > 1:
            try:
                black_list_register.remove(ip)
            except:
                pass

        # return message if ip blacklisted
        if ip in black_list_register:
            start_register = time.time()
            return render_template('register.html', message='Wait 1 second!')

        # blacklist ip
        black_list_register.append(ip)
        start_register = time.time()


        # SANITIZE ERRORS

        # no username
        if not request.form.get('username'):
            return render_template('register.html', message='Username missing!')

        # username too long
        if len(request.form.get('username')) > 26:
            return render_template('register.html', message='Username too long!')

        # blank space in username
        if ' ' in request.form.get('username'):
            return render_template('register.html', message='No blank spaces allowed!')

        # username already exists
        db_cursor.execute("SELECT * FROM users WHERE username = (?)",
        [request.form.get('username')]
        )
        if db_cursor.fetchall():
            return render_template('register.html', message='Username already exists!')

        # no password
        if not request.form.get('password'):
            return render_template('register.html', message='Password missing!')

        # no confirmation
        if not request.form.get('confirmation'):
            return render_template('register.html', message='Confirmation password missing!')

        # password size
        if len(request.form.get('password')) < 8:
            return render_template('register.html', message='Password must be at least 8 characters!')

        # password too long
        if len(request.form.get('password')) > 256:
            return render_template('register.html', message='Password too long!')

        # different passwords
        if request.form.get('password') != request.form.get('confirmation'):
            return render_template('register.html', message='Passwords do not match!')

        # IF SUCCESSFUL
        hash_password = generate_password_hash(request.form.get('password'), salt_length=13)

        # register user in database
        db_cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)",
        [request.form.get('username'),
        hash_password]
        )
        db.commit()

        # select all users
        global users
        db_cursor.execute('SELECT * FROM users')
        users = db_cursor.fetchall()

        flash('Succesfully registered!')
        return redirect('/login')

    # method GET
    else:
        return render_template('register.html')


# reset password
@app.route('/resetpassword', methods=['GET', 'POST'])
def reset():
    if request.method == "POST":
        global user_by_token

        # if not e-mail registered:
        db_cursor.execute('SELECT * FROM users WHERE username = (?)',
        [request.form.get('username')]
        )
        requested_user = db_cursor.fetchone()

        # no user registered
        if not requested_user:
            return render_template('reset2.html', error_msg='Username not registered')

        # no e-mail registered for this user
        if not requested_user[3]:
            return render_template('reset2.html', error_msg='E-mail address not registered')

        user_mail = requested_user[3]

        # generate token
        token = serializer.dumps(user_mail, salt='email-confirm')
        user_by_token[token] = requested_user
        token_url = url_for('reset_with_token', token=token, _external=True)

        # send e-mail
        message = Message('Reset your password - Bearing support', recipients=[user_mail]) #EDIT LATER / USE DATABASE E-MAIL
        message.body = 'Your password redefinition link is ' + token_url
        mail.send(message)

        # hide user e-mail
        user_mail = list(user_mail)
        for i in range (1, len(user_mail)-1):
            if user_mail[i] != '@' and user_mail[i] != '.' and user_mail[i+1] != '@':
                user_mail[i] = '*'
        user_mail[len(user_mail)-1] = '*'

        user_mail = ''.join(user_mail)

        return render_template('reset2.html', success_msg='Reset password link was sent to ' + user_mail + ' and it will expire soon.')


    # method GET
    else:
        return render_template('reset.html')


# reset password with token
@app.route('/redefinepassword/<token>', methods=['GET', 'POST'])
def reset_with_token(token):

    global user_by_token

    user_by_token[token]

    # method POST
    if request.method == "POST":

        # no password
        if not request.form.get('password'):
            return render_template('reset3.html', user=user_by_token[token], token=token, msg='Password missing!')

        # no confirmation
        if not request.form.get('confirmation'):
            return render_template('reset3.html', user=user_by_token[token], token=token, msg='Confirmation password missing!')

        # different passwords
        if request.form.get('password') != request.form.get('confirmation'):
            return render_template('reset3.html', user=user_by_token[token], token=token, msg='Passwords do not match!')

        # IF SUCCESSFUL
        hash_password = generate_password_hash(request.form.get('password'), salt_length=13)

        # register user in database
        db_cursor.execute("UPDATE users SET password = (?) WHERE id = (?)",
        [hash_password,
        user_by_token[token][0]]
        )
        db.commit()

        # destroy token
        user_by_token.clear()
        token = ''

        #clear session
        session.clear()

        flash('Password succesfully redefined!')
        return redirect('/login')

    # method GET
    else:
        try:
            email = serializer.loads(token, salt='email-confirm', max_age=1800)
        except:
            return 'link not working'

        return render_template('reset3.html', user=user_by_token[token], token=token)

# index
@app.route('/')
def index():

    # login required
    if not session.get('user_id'):
        return render_template('about.html')


    # get user's cards
    db_cursor.execute('SELECT * FROM cards WHERE id = (?)',
    [session['user_id']])
    cards = db_cursor.fetchall()

    # get user's examples
    examples = []
    for card in cards:
        db_cursor.execute('SELECT text FROM examples WHERE id = (?)',
        [card[1]],
        )
        examples.append(db_cursor.fetchall())

    # get cards example_amount
    examples_amount = []
    for card in cards:
        db_cursor.execute('SELECT COUNT(*) FROM examples WHERE id = (?)',
        [card[1]]
        )
        examples_amount.append(db_cursor.fetchone()[0])

    # footer message
    cards_amount = str(len(cards))

    if not cards:
        footer = "You do not have any cards yet."

    elif int(cards_amount) == 1:
        footer = "You have only 1 card."
    else:
        footer = "You have " + cards_amount + " cards."

    return render_template('index.html', user=session['user'], cards=cards, examples=examples, examples_amount=examples_amount, footer=footer)


# add
@app.route('/add', methods=['GET', 'POST'])
def add():

    # login required
    if not session.get('user_id'):
        return redirect('/')

    # method POST
    if request.method == 'POST':

        # ADD CARD TO DATABASE

        # add word and definition
        db_cursor.execute("INSERT INTO cards (id, word, definition) VALUES (?, ?, ?)",
            [session['user_id'],
            request.form.get('word'),
            request.form.get('definition'),]
            )

        card_index = db_cursor.lastrowid

        # add examples to example_list
        example_list = []
        n = int(request.form.get('num'))
        for i in range(0, n):
            if request.form.get('example'+str(i)):
                example_list.append(request.form.get('example'+str(i)))

        # add examples from example_list
        for example in example_list:
            db_cursor.execute("INSERT INTO examples (text, id) VALUES (?, ?)",
            [example,
            card_index]
            )
        db.commit()

        return render_template('add.html', user=session['user'], message='Succesfully added card!')

    # method GET
    else:
        return render_template('add.html', user=session['user'])


# edit card
@app.route('/edit_card', methods=['GET', 'POST'])
def edit_card():

    # login required
    if not session.get('user_id'):
        return redirect('/')

    global cards, examples

    # method POST
    if request.method == 'POST':

        card_id = cards[session['card_id']][1]

        # update CARD IN DATABASE
        word = request.form['data[0][value]']
        definition = request.form['data[1][value]']

        # card do not belong to user
        db_cursor.execute('SELECT * FROM cards WHERE id = (?) AND card_id = (?)',
        [session['user_id'],
        card_id]
        )
        if not all(db_cursor.fetchall()):
            return ':('

        # add word and definition
        db_cursor.execute("UPDATE cards SET word = (?), definition = (?) WHERE card_id = (?) and id = (?)",
            [word,
            definition,
            card_id,
            session['user_id']]
            )

        # delete exemples
        db_cursor.execute('DELETE FROM examples WHERE id = (?) AND id IN (SELECT id FROM cards WHERE id = (?))',
        [card_id,
        session['user_id']]
        )

        # add examples to example_list
        example_list = []
        length = int((len(request.form)-2)/2)
        for i in range(2, length):
            example_list.append(str(request.form['data['+str(i)+'][value]']))

        # add examples from example_list
        for example in example_list:
            db_cursor.execute("INSERT INTO examples (text, id) VALUES (?, ?)",
            [example,
            card_id]
            )
        db.commit()

        # UPDATE CARDS AND EXAMPLES

        # get user's cards
        db_cursor.execute('SELECT * FROM cards WHERE id = (?)',
        [session['user_id']])
        cards = db_cursor.fetchall()

        # get user's examples
        db_cursor.execute('SELECT * FROM examples WHERE id IN (SELECT card_id from cards WHERE id = (?))',
        [session['user_id']],
        )
        examples = db_cursor.fetchall()

        return ''

    # method GET
    else:

        card_id = session['card_id']

        # get user's card
        card = cards[card_id]

        # get card's examples
        card_examples = []
        for example in examples:
            if example[0] == card[1]:
                card_examples.append(example[1])

        result = {'card': card, 'examples': card_examples}

        return render_template('edit.html', user=session['user'], result=result)



# delete card
@app.route('/delete_card', methods=['POST'])
def delete_card():

    # login required
    if not session.get('user_id'):
        return redirect('/')


    global cards, examples

    card_id = cards[session['card_id']][1]

    # delete cards
    db_cursor.execute('DELETE FROM cards WHERE card_id = (?)',
    [card_id]
    )

    # delete examples
    db_cursor.execute('DELETE FROM examples WHERE id in (SELECT card_id FROM cards WHERE card_id = (?))',
    [card_id]
    )

    # update sequence
    db_cursor.execute('UPDATE sqlite_sequence SET seq = 0')

    db.commit()

    # UPDATE CARDS AND EXAMPLES

    # get user's cards
    db_cursor.execute('SELECT * FROM cards WHERE id = (?)',
    [session['user_id']])
    cards = db_cursor.fetchall()

    # get user's examples
    db_cursor.execute('SELECT * FROM examples WHERE id IN (SELECT card_id from cards WHERE id = (?))',
    [session['user_id']],
    )
    examples = db_cursor.fetchall()

    return ''


# Google Custom Search API
@app.route('/image_search')
def image_search():

    # login required
    if not session.get('user_id'):
        return redirect('/')

    keyword = request.args.get('keyword')
    resource = build('customsearch', 'v1', developerKey=os.environ.get('API_KEY')).cse()
    results = resource.list(q=keyword, cx=os.environ.get('SearchEngineId'), searchType='image').execute()
    result = []
    for item in results['items']:
        result.append({'title': item['title'], 'link': item['link']})

    result = jsonify(result)
    return result


# RapidAPI Web Search API
@app.route('/image_search2')
def image_search2():

    # login required
    if not session.get('user_id'):
        return redirect('/')

    keyword = request.args.get('keyword')
    url = "https://contextualwebsearch-websearch-v1.p.rapidapi.com/api/Search/ImageSearchAPI"
    querystring = {"q": keyword,"pageNumber":"1","pageSize":"12","autoCorrect":"false","safeSearch":"true"}
    headers = {
        'x-rapidapi-key': os.environ.get('x-rapidapi-key'),
        'x-rapidapi-host': os.environ.get('x-rapidapi-host')
        }

    response = requests.request("GET", url, headers=headers, params=querystring).json()

    return response


# study
@app.route('/study', methods=['GET', 'POST'])
def study():

    # login required
    if not session.get('user_id'):
        return redirect('/')

    if request.method == 'POST':

        # golbal card and examples
        global cards, examples

        # get user's cards
        db_cursor.execute('SELECT * FROM cards WHERE id = (?)',
        [session['user_id']]
        )
        cards = db_cursor.fetchall()

        # get user's examples-
        db_cursor.execute('SELECT * FROM examples WHERE id IN (SELECT card_id from cards WHERE id = (?))',
        [session['user_id']],
        )
        examples = db_cursor.fetchall()

        # global card_id: stores card's id
        session['card_id'] = 0

        #IF USER HAS NO CARDS
        if not cards:
            return render_template('nocards.html', user=session['user'])

        return render_template('study.html', user=session['user'])

    else:
        # get user's cards
        db_cursor.execute('SELECT * FROM cards WHERE id = (?)',
        [session['user_id']]
        )
        cards = db_cursor.fetchall()
        #IF USER HAS NO CARDS
        if not cards:
            return render_template('nocards.html', user=session['user'])

        return render_template('start_study.html', user=session['user'])


# get card
@app.route('/get_card')
def get_card():

    # login required
    if not session.get('user_id'):
        return redirect('/')

    global cards, examples
    card_id = session['card_id']

    # update reviewed cards
    db_cursor.execute('UPDATE users SET reviewed_cards = reviewed_cards + 1 WHERE id = (?)',
    [session['user_id']]
    )
    db.commit()

    try:

        if request.args.get('actual'):
            # SPECIFIC CARD
            card_id = session['card_id']

            # get user's card
            card = cards[card_id]

            # get card's examples
            card_examples = []
            for example in examples:
                if example[0] == card[1]:
                    card_examples.append(example[1])

            # is card left
            card_left = True
            if session.get('card_id') <= 0:
                card_left = False

            result = {'card': card, 'examples': card_examples, 'card_left': card_left}
            return jsonify(result)


        # SPECIFIC CARD
        elif request.args.get('id'):

            #specific card id
            session['card_id'] = int(request.args.get('id'))

            card_id = session['card_id']

            # get user's card
            card = cards[card_id]

            # get card's examples
            card_examples = []
            for example in examples:
                if example[0] == card[1]:
                    card_examples.append(example[1])

            # is card left
            card_left = True
            if session.get('card_id') <= 0:
                card_left = False


            result = {'card': card, 'examples': card_examples, 'card_left': card_left}
            return jsonify(result)

        # PREVIOUS
        elif request.args.get('left'):
            # go back 1 card
            session['card_id'] -= 1
            card_id = session['card_id']

            # get user's card
            card = cards[card_id]

            # get card's examples
            card_examples = []
            for example in examples:
                if example[0] == card[1]:
                    card_examples.append(example[1])

            # is card left
            card_left = True
            if session.get('card_id') <= 0:
                card_left = False

            result = {'card': card, 'examples': card_examples, 'card_left': card_left}
            return jsonify(result)

        # NEXT
        else:
            # skip 1 card
            print(session['card_id'])
            session['card_id'] += 1
            card_id = session['card_id']
            print(session['card_id'])

            # get user's card
            card = cards[card_id]

            # get card's examples
            card_examples = []
            for example in examples:
                if example[0] == card[1]:
                    card_examples.append(example[1])
            print(session['card_id'])
            # is card left
            card_left = True
            if session.get('card_id') <= 0:
                card_left = False
            print(session['card_id'])
            result = {'card': card, 'examples': card_examples, 'card_left': card_left}
            return jsonify(result)
    except:
        # update reviewed cards
        db_cursor.execute('UPDATE users SET reviewed_cards = reviewed_cards - 1 WHERE id = (?)',
        [session['user_id']]
        )
        db.commit()
        return False


# add time
black_list_add = []
start_add = time.time()

@app.route('/add_time', methods=['POST'])
def add_time():

    # login required
    if not session.get('user_id'):
        return redirect('You must be logged in for performing this action!'), 403


    # BLACK LIST
    global black_list_add, start_add

    # unblacklist user
    print(time.time() - start_add)
    if time.time() - start_add > .95:
        try:
            black_list_add.remove(session.get('user_id'))
        except:
            pass

    # return message if user blacklisted
    if session.get('user_id') in black_list_add:
        return 'Wait 1 second between each time adding request!', 403

    # blacklist user
    black_list_add.append(session.get('user_id'))
    start_add = time.time()

    #add time
    db_cursor.execute('UPDATE users SET studied_time = studied_time + 1 WHERE id = (?)',
    [session['user_id']]
    )
    db.commit()
    return 'Success', 200

# user area
@app.route('/user/<username>', methods=['GET', 'POST'])
def profile(username):

    global users

    if not session.get('user_id'):
        session['user'] = False

    db_cursor.execute('SELECT * FROM users WHERE username = (?)',
    [username]
    )
    p_user = db_cursor.fetchone()

    try:
        if username == p_user[1]:
            # medals=medals
            medals = []
            db_cursor.execute('SELECT COUNT(*) FROM cards WHERE id = (?)',
            [p_user[0]]
            )
            medals.append(db_cursor.fetchone()[0])

            db_cursor.execute('SELECT reviewed_cards FROM users WHERE id = (?)',
            [p_user[0]]
            )
            medals.append(db_cursor.fetchone()[0])

            db_cursor.execute('SELECT studied_time FROM users WHERE id = (?)',
            [p_user[0]]
            )
            medals.append(db_cursor.fetchone()[0])

            # can edit
            edit = False
            try:
                if session.get('user_id') == p_user[0]:
                    edit = True
            except:
                edit = False

            # method POST
            if request.method == 'POST':

                display = True

                # SANITIZE ERRORS

                # DIFFERENTE USERS
                if session.get('user_id') != p_user[0]:
                    flash('Oops! you can only edit your own profile')
                    return render_template('user.html', user=session['user'], p_user=p_user, medals=medals, edit=edit, display=display)

                # USERNAME
                # no username
                if not request.form.get('username'):
                    return render_template('register.html', message='Username missing!')

                # username too long
                if len(request.form.get('username')) > 26:
                    flash('Username must be less than or equal to 26 characters!')
                    return render_template('user.html', user=session['user'], p_user=p_user, medals=medals, edit=edit, display=display)

                # blank space in username
                if ' ' in request.form.get('username'):
                    flash('No blank spaces allowed!')
                    return render_template('user.html', user=session['user'], p_user=p_user, medals=medals, edit=edit, display=display)

                # username already exists
                db_cursor.execute("SELECT * FROM users WHERE username = (?) AND id != (?)",
                [request.form.get('username'),
                session['user_id']]
                )
                if db_cursor.fetchall():
                    flash('Username already exists!')
                    return render_template('user.html', user=session['user'], p_user=p_user, medals=medals, edit=edit, display=display)

                # MAIL
                # wrong mail format
                if request.form.get('mail'):
                    mail = request.form.get('mail')
                    if not '@' in mail or not '.' in mail or 3 > len(mail) or len(mail) > 64:
                        flash('E-mail not allowed!')
                        return render_template('user.html', user=session['user'], p_user=p_user, medals=medals, edit=edit, display=display)

                # URL
                # not url
                if request.form.get('url'):
                    if not is_url_image(request.form.get('url')):
                        flash('Profile image URL not recognized!')
                        return render_template('user.html', user=session['user'], p_user=p_user, medals=medals, edit=edit, display=display)

                # BANNER URL
                # not url
                if request.form.get('banner_url'):
                    if not is_url_image(request.form.get('banner_url')):
                        flash('Background URL not recognized!')
                        return render_template('user.html', user=session['user'], p_user=p_user, medals=medals, edit=edit, display=display)

                # DESCRIPTION
                # description size
                if len(request.form.get('username')) > 256:
                    return render_template('register.html', message='Description must be less than 256 characters!')

                # UPDATE
                new_username = str(request.form.get('username'))
                new_mail = str(request.form.get('mail'))
                new_url = str(request.form.get('url'))
                new_banner_url = str(request.form.get('banner_url'))
                new_description = str(request.form.get('description'))

                db_cursor.execute('UPDATE users SET username = (?), mail = (?), image = (?), background = (?), description = (?) WHERE id = (?)',
                [new_username,
                new_mail,
                new_url,
                new_banner_url,
                new_description,
                session['user_id']]
                )
                db.commit()


                db_cursor.execute('SELECT * FROM users WHERE id = (?)',
                [session['user_id']]
                )
                session['user'] = db_cursor.fetchone()

                db_cursor.execute('SELECT * FROM users')
                users = db_cursor.fetchall()

                p_user = session['user']

                msg = 'Sucesfully updated!'

                return render_template('user.html', user=session['user'], p_user=p_user, medals=medals, edit=edit, display=display, msg=msg)

            # method GET
            else:

                return render_template('user.html', user=session['user'], p_user=p_user, medals=medals, edit=edit)

    except:
        # profile doesn't exist
        try:
            return render_template("apology.html", user=session['user'], code='Oops!', phrase='Sorry, this profile does not exist'), 404
        except:
            return render_template("apology.html", user=False, code='Oops!', phrase='Sorry, this profile does not exist'), 404


# logout
@app.route('/logout', methods=['POST'])
def logout():

    # login required

    if not session.get('user_id'):
        return redirect('/')

    session.clear()
    return redirect('/')

# delete
@app.route('/delete', methods=['POST'])
def delete():

    # login required
    if not session.get('user_id'):
        return redirect('/')

    # delete user
    db_cursor.execute('DELETE FROM users WHERE id = (?)',
    [session['user_id']]
    )

    # delete cards
    db_cursor.execute('DELETE FROM cards WHERE id = (?)',
    [session['user_id']]
    )

    # delete examples
    db_cursor.execute('DELETE FROM examples WHERE  id in (SELECT card_id FROM cards WHERE id = (?))',
    [session['user_id']]
    )

    # clear session
    session.clear()

    # update sequence
    db_cursor.execute('UPDATE sqlite_sequence SET seq = 0')

    db.commit()

    return redirect('/')


# all status code
codes = list(HTTPStatus)[22:]

# remove codes
for rmv_code in [402, 407, 421, 425, 426, 506, 507, 508, 510, 511]:
    if rmv_code in codes:
        codes.remove(rmv_code)

# handle errors
for code in codes:
    @app.errorhandler(code.value)
    def page_not_found(e):

        if not session:
            session['user'] = False

        return render_template('apology.html', user=session['user'], code=code.value, phrase=code.phrase), code.value



# Use functions globally in jinja
app.jinja_env.globals.update(fit=fit)
app.jinja_env.globals.update(is_url_image=is_url_image)

# run app
if __name__ == '__main__':
    app.run()
