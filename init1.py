#Import Flask Library
from flask import Flask, render_template, request, session, url_for, redirect
import pymysql.cursors



#Initialize the app from Flask
app = Flask(__name__)

#Configure MySQL
conn = pymysql.connect(host='localhost',
                       port = 8889,
                       user='root',
                       password='root',
                       db='pricosha',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)

#Define a route to hello function
@app.route('/')
def hello():
    return render_template('index.html')

#Define route for login
@app.route('/login')
def login():
    return render_template('login.html')

#Define route for register
@app.route('/register')
def register():
    return render_template('register.html')

#Authenticates the login
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    #grabs information from the forms
    email = request.form['email']
    password = request.form['password']

    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM person WHERE email = %s and password = SHA2(%s, 256)' 
    cursor.execute(query, (email, password))
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
    cursor.close()
    error = None

    if(data):
        #creates a session for the the user
        #session is a built in
        session['email'] = email
        return redirect(url_for('home'))
    else:
        #returns an error message to the html page
        error = 'Invalid login or username'
        return render_template('login.html', error=error)

#Authenticates the register
@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
    #grabs information from the forms
    email = request.form['email']
    password = request.form['password']
    f_name = request.form['f_name']
    l_name = request.form['l_name']

    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM person WHERE email = %s'
    cursor.execute(query, (email))
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
    error = None

    if(data):
        #If the previous query returns data, then user exists
        error = "This user already exists"
        return render_template('register.html', error = error)
    else:
        ins = 'INSERT INTO person VALUES(%s, SHA2(%s, 256), %s, %s)'
        cursor.execute(ins, (email, password, f_name, l_name))
        conn.commit()
        cursor.close()
        return render_template('index.html')


@app.route('/home')
def home():
    person = session['email']
    email = session['email']
    cursor = conn.cursor();
    query = 'SELECT post_time, item_name FROM ContentItem WHERE email_post = %s ORDER BY post_time DESC'
    cursor.execute(query, (person))
    data = cursor.fetchall()


    q_to_check_fg_validity_1 = '''SELECT fg_name FROM Friendgroup WHERE owner_email = %s'''
    cursor.execute(q_to_check_fg_validity_1, (email))
    fg_dict1 = cursor.fetchall() #returns a list of dictionaries
    fg_list1 = []

    if len(fg_dict1) > 0:
        i = 0
        while i < len(fg_dict1):
            fg_list1.append(fg_dict1[i]['fg_name'])
            i+=1


    q_to_check_fg_validity_2 = '''SELECT fg_name FROM Belong WHERE email = %s'''
    cursor.execute(q_to_check_fg_validity_2, (email))
    fg_dict2 = cursor.fetchall()
    fg_list2 = []

    if len(fg_dict2) > 0:
        i = 0
        while i < len(fg_dict2):
            fg_list2.append(fg_dict2[i]['fg_name'])
            i+=1

    fg_list = fg_list1 + list(set(fg_list2) - set(fg_list1))

    cursor.close()
    return render_template('home.html', person=person, posts=data, fg_list=fg_list, fg_list_own=fg_list1)

@app.route('/post', methods=['GET', 'POST'])
def post():
    email = session['email']
    item_name = request.form['item_name']
    file_path = request.form['file_path']
    is_pub = request.form['is_pub']
    fg_to_share = request.form['fg_to_share']
    fg_to_share = fg_to_share.split(", ")

    cursor = conn.cursor()
    q = '''INSERT INTO ContentItem (email_post, post_time, file_path, item_name, is_pub) 
               VALUES (%s, CURRENT_TIMESTAMP(), %s, %s, %s)'''

    cursor.execute(q, (email, file_path, item_name, is_pub))

    q_to_get_id = '''
            SELECT item_id
            FROM ContentItem
            WHERE item_id = (SELECT MAX(item_id) from ContentItem);
        ''' 

    cursor.execute(q_to_get_id)
    tmp_id = cursor.fetchone()

    if is_pub == '0':
        ins = '''
           INSERT INTO Share (owner_email, fg_name, item_id) VALUES (%s, %s, %s)
           '''
        for fg_name in fg_to_share:
            cursor.execute(ins, (email, fg_name, tmp_id['item_id']))
    
    conn.commit()
    cursor.close()
    return redirect(url_for('home'))

@app.route('/add_friend', methods=['GET', 'POST'])
def add_friend():
    email = session['email']
    friendgroup_name = request.form['friend_group']
    friend_f_name = request.form['new_friend_f_name']
    friend_l_name = request.form['new_friend_l_name']
    cursor = conn.cursor()

    q_get_friend_email = '''SELECT email FROM Person WHERE fname = %s and lname = %s'''
    cursor.execute(q_get_friend_email, (friend_f_name, friend_l_name))
    new_friend_email_tmp = cursor.fetchone()
    new_friend_email = new_friend_email_tmp['email']


    q_ins_new_friend = '''INSERT INTO Belong (email, owner_email, fg_name) VALUES (%s, %s, %s)'''

    cursor.execute(q_ins_new_friend, (new_friend_email, email, friendgroup_name))

    conn.commit()
    cursor.close()
    return redirect(url_for('home'))

@app.route('/view_public_content', methods=["GET", "POST"])
def view_public_content():
    #is_pub = request.form['is_pub']
    cursor = conn.cursor();
    query = 'SELECT item_id, email_post,post_time,file_path,item_name FROM ContentItem ci WHERE is_pub = 1 AND ci.post_time >= DATE_SUB(NOW(),INTERVAL 1 DAY)'
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    return render_template('view_public.html',posts=data)

@app.route('/shared_content', methods = ["GET", "POST"])
def shared_content():
    email = session['email']
    cursor = conn.cursor();
    query = 'SELECT * FROM contentitem WHERE item_id IN ( SELECT item_id FROM contentitem LEFT OUTER JOIN (share NATURAL JOIN belong) USING (item_id) WHERE email=%s OR is_pub = 1) OR item_id IN (SELECT item_id FROM contentitem WHERE email_post = %s) ORDER BY post_time DESC'
    cursor.execute(query, (email, email))
    data = cursor.fetchall()
    cursor.close()

    cursor = conn.cursor();
    query = 'SELECT email,fname,lname FROM person'
    cursor.execute(query)
    data_1 = cursor.fetchall()
    cursor.close()

    cursor = conn.cursor();
    query = 'SELECT * FROM `tag` join person on tag.email_tagged = person.email WHERE status = 1'
    cursor.execute(query)
    data_2 = cursor.fetchall()
    cursor.close()

    cursor = conn.cursor();
    query = 'SELECT * FROM rate'
    cursor.execute(query)
    data_3 = cursor.fetchall()
    cursor.close()

    return render_template('shared_content.html', posts = data, posts1 = data_1, posts2= data_2, posts3 = data_3)

@app.route('/manage_tags', methods = ["GET", "POST"])
def manage_tags():
    tagee = session['email']
    tagger = request.form.get('tagger', False)
    status_approval = request.form.get('status', False)
    item_id = request.form.get('item_id', False)


    cursor = conn.cursor()

    if status_approval == 'accept':
        cursor.execute('UPDATE Tag SET status = 1 WHERE item_id = %s AND email_tagged = %s AND email_tagger = %s ', (item_id, tagee, tagger))

    else:
        cursor.execute('DELETE FROM Tag WHERE item_id = %s AND email_tagged = %s AND email_tagger = %s', (item_id, tagee, tagger))

    cursor.execute('SELECT * FROM tag WHERE status = 0 and email_tagged = %s', tagee)
    data = cursor.fetchall()

    conn.commit()
    cursor.close()

    """
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tag WHERE status = 0 and email_tagged = %s', tagee)
    data = cursor.fetchall()

    cursor.close() """

    return render_template('manage_tags.html', posts = data, tagee = tagee)

@app.route('/password')
def password():
    return render_template('password.html')

@app.route('/forgot_password', methods=['GET','POST']) #cosmetic changes needed
def forgot_password():
    email = request.form['email']
    new_pass = request.form['new_password']

    cursor = conn.cursor()

    q = 'SELECT * FROM Person WHERE email=%s'
    cursor.execute(q, (email))
    data = cursor.fetchone()
    cursor.close()

    cursor = conn.cursor()
    update = 'UPDATE Person SET password = SHA2(%s, 256) WHERE email = %s'
    cursor.execute(update, (new_pass, email))
    conn.commit()

    q = 'SELECT * FROM person WHERE email = %s AND password = %s'
    cursor.execute(q, (email, new_pass))

    new_data = cursor.fetchone()
    print(new_data)
    cursor.close()
    return render_template('index.html')

@app.route('/tag', methods = ["GET", "POST"])
def tag():
    tagger = session['email']
    tagged = request.form. get('tagged', False)
    item_id = request.form.get('item_id', False)
    item_id = int(item_id)
    error = None

    #data visible to the person logged-in
    cursor = conn.cursor()
    query = '''SELECT * FROM contentitem WHERE item_id IN ( SELECT item_id FROM contentitem LEFT OUTER JOIN (share NATURAL JOIN belong) USING (item_id) WHERE email=%s OR is_pub = 1) OR item_id IN (SELECT item_id FROM contentitem WHERE email_post = %s) ORDER BY post_time DESC'''
    cursor.execute(query, (tagger, tagger))
    data = cursor.fetchall()
    cursor.close()

    cursor = conn.cursor()
    query = '''SELECT Tag.tagtime, Tag.email_tagged, Tag.item_id, Person.fname, Person.lname FROM Tag NATURAL JOIN Person WHERE Tag.email_tagged = Person.email ORDER BY item_id DESC'''
    cursor.execute(query)
    tags = cursor.fetchall()
    cursor.close()

    cursor = conn.cursor()
    query = "SELECT * FROM Comment "
    cursor.execute(query)
    comments = cursor.fetchall()
    cursor.close()

    cursor = conn.cursor();
    query = 'SELECT * FROM rate'
    cursor.execute(query)
    data_3 = cursor.fetchall()
    cursor.close()

    cursor = conn.cursor();
    query = 'SELECT * FROM `tag` join person on tag.email_tagged = person.email WHERE status = 1'
    cursor.execute(query)
    data_2 = cursor.fetchall()
    cursor.close()


    cursor = conn.cursor()
    if tagged == tagger:
        status = 1
        cursor.execute('INSERT INTO Tag (email_tagged, email_tagger,item_id, status) VALUES(%s,%s,%s,%s) ', (tagged, tagger, item_id, status))

    else:
        status = 0
        if(tagged != False and item_id != False):

            q_visible_to_person = '''SELECT * FROM contentitem WHERE item_id IN ( SELECT item_id FROM contentitem LEFT OUTER JOIN (share NATURAL JOIN belong) USING (item_id) WHERE email=%s OR is_pub = 1) OR item_id IN (SELECT item_id FROM contentitem WHERE email_post = %s) ORDER BY post_time DESC'''
            cursor.execute(q_visible_to_person, (tagged, tagged))
            tagged_can_view_tmp = cursor.fetchall() #list of dictionaries
            tagged_can_view = []

            if len(tagged_can_view_tmp) == 0: error = "User that you tried to tag cannot view this content item."

            if len(tagged_can_view_tmp) > 0:
                i = 0
                while i < len(tagged_can_view_tmp):
                    tagged_can_view.append(tagged_can_view_tmp[i]['item_id'])
                    i+=1



                if item_id in tagged_can_view:
                    print('blha')
                    cursor.execute('INSERT INTO Tag (email_tagged, email_tagger,item_id, status) VALUES(%s,%s,%s,%s) ', (tagged, tagger, item_id, status))
                    conn.commit()
                else:
                    error = "User that you tried to tag cannot view this content item."


    cursor.close()

    if error == None:
        return render_template('tag.html', posts = data, tags = tags,  comments=comments, posts3 = data_3, posts2 = data_2)
    else:
        cursor.close()
        return render_template('tag.html', posts = data, tags = tags, comments=comments, posts3 = data_3, posts2 = data_2, error=error)


@app.route('/comment', methods = ["GET", "POST"])
def comment():

    email = session['email']
    comment_text = request.form.get('comment', False)
    item_id = request.form.get('item_id', False)

    if(item_id != False and comment_text != False):
        cursor = conn.cursor()
        query = 'INSERT INTO Comment (item_id, email, comment_text) VALUES(%s, %s, %s)'
        cursor.execute(query, (item_id, email, comment_text))
        conn.commit()
        cursor.close()

    return redirect(url_for('tag'))



@app.route('/logout')
def logout():
    session.pop('email')
    return redirect('/')
        
app.secret_key = 'some key that you will never guess'
#Run the app on localhost port 5000
#debug = True -> you don't have to restart flask
#for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug = True)
