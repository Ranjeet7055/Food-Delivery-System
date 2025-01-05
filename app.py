import re
import random
import time
from flask import Flask, request, jsonify, render_template, session, flash, redirect, url_for
from flask_mail import Mail, Message
import sqlite3
import secrets
import atexit

app = Flask(__name__)
app.secret_key = 'mysecrethifi'
def init_db():
    try:
        conn = sqlite3.connect("database.db",timeout=30)
        conn.execute("PRAGMA journal_mode=WAL;")  # Enable WAL for better concurrency
        cursor = conn.cursor()
        #Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                location TEXT,
                contact TEXT,
                approved INTEGER NOT NULL DEFAULT 0  -- 0 = pending, 1 = approved, -1 = rejected
            )
        """)
        #Delivery Agent Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Delivery_Agent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                location TEXT,
                contact TEXT,
                approved INTEGER NOT NULL DEFAULT 0  -- 0 = pending, 1 = approved, -1 = rejected
            )
        """)
        # Contact messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contact_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                message TEXT NOT NULL
            )
        ''')    
        conn.commit()
    except sqlite3.OperationalError as e:
        print(f"Error initialising database: {e}")
    finally:
        conn.close() #Always close the connection
init_db()

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'hifidelivery213@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'oiya zlhv irvc yowz'  # Replace with your app-specific password

mail = Mail(app)
# Store OTPs in memory (can be changed to a database in production)
# otp_store = {}

# # Send OTP to the email
# def send_otp(email, otp):
#     try:
#         msg = Message('Your OTP Code', sender=app.config['MAIL_USERNAME'], recipients=[email])
#         msg.body = f"Your OTP code is {otp}. It will expire in 10 minutes."
#         mail.send(msg)
#         print(f"OTP sent to {email}")
#     except Exception as e:
#         print(f"Error sending OTP: {e}")
#         return False
#     return True

@app.route('/home') 
def start():
    return render_template('homepage.html')

# @app.route('/send_otp', methods=['POST'])
# def send_otp_route():
#     data = request.get_json()
#     email = data.get('email')

#     if not email or not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
#         return jsonify({'success': False, 'message': 'Invalid email format.'})

#     otp = str(random.randint(100000, 999999))
#     otp_store[email] = {'otp': otp, 'timestamp': time.time()}  # Store OTP with timestamp

#     if send_otp(email, otp):
#         return jsonify({'success': True, 'message': 'OTP sent to email.'})
#     else:
#         return jsonify({'success': False, 'message': 'Error sending OTP.'})

@app.route('/',methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM users WHERE username = ? AND password = ?
            """, (username, password))
            user = cursor.fetchone()
            is_agent=False
            if not user:
                #check in delivery table if not found in users table
                cursor.execute(""" SELECT * FROM Delivery_Agent WHERE username = ? AND password = ?""",(username,password))
                user=cursor.fetchone()
                is_agent=True if user else False
                
            
            if user:
                #extract user details and set session variables
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['email'] = user[2]
                session['role'] = user[4] if not is_agent else 'Delivery Agent'
                session['location'] = user[5] if len(user) > 5 else 'Not Provided'
                session['contact'] = user[6] if len(user) > 6 else 'Not Provided'
                
                if session['role'].lower() == 'admin' and password == "123456":
                    flash('Login successful! Welcome back, Admin.', 'success')
                    return redirect(url_for('admin'))  # Redirect to Admin dashboard
                elif is_agent:
                    flash('Login successful! Welcome back, Delivery Agent.', 'success')
                    return redirect(url_for('delivery'))  # Redirect to Delivery Agent dashboard
                else:
                    flash('Login successful! Welcome back, Customer.', 'success')
                    return redirect(url_for('start'))  # Redirect to Customer dashboard
            else:
                flash('Invalid username or password. Please try again.', 'danger')

    return render_template('login.html')

def get_db_connection():
    conn = sqlite3.connect('database.db', timeout=30)  # Timeout to avoid lock
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        role = request.form['role']
        confirm_password = request.form['confirm_password']
        location = request.form['location']
        contact = request.form['contact']

        print(f'Role received:{role}')
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                print("Connection opened successfully.")
                if role.lower() == "deliveryagent":
                    cursor.execute("""
                    INSERT INTO Delivery_Agent (username, password, email, role, location, contact)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (username, password, email, role, location, contact))
                else:
                    cursor.execute("""
                    INSERT INTO users (username, password, email, role, location, contact)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (username, password, email, role, location, contact))
                
                conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.OperationalError as e:
            flash(f'Database is currently locked: {e}', 'danger')
        except sqlite3.IntegrityError:
            flash('Username or email already exists. Please use another.', 'danger')
        except Exception as e:
            flash(f'Error during Registration: {e}','danger')
            
    return render_template('register.html')  # Ensure register.html is your registration page

@app.route('/info')
def info():
    return render_template('info.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        message = request.form['message']
        print(name)
        try:
            # Connect to the database
            with sqlite3.connect('database.db') as conn:
                cursor = conn.cursor()
                # Perform a case-insensitive check using COLLATE NOCASE
                cursor.execute('select * from users where email = ?',(email,))
                user = cursor.fetchone()

                if user:
                    # Insert the contact message into the 'contact_messages' table
                    cursor.execute('''
                        INSERT INTO contact_messages (name, email, message)
                        VALUES (?, ?, ?)
                    ''', (name, email, message))
                    conn.commit()
                    flash("Feedback taken successfully", "success")
                else:
                    flash("Email  does not exist", "danger")

        except sqlite3.Error as e:
            flash(f"An error occurred: {str(e)}", "danger")

    return render_template('contact.html')


# @app.route('/forgot')
# def forgot():
#     return render_template('forgot.html')
#forgot password
@app.route('/forgot')
def forgot():
    return render_template('forgot.html')

# Route for handling recovery form submission
@app.route('/recovery', methods=['GET', 'POST'])
def recovery():
    if request.method == 'POST':
        email = request.form['email']
        
        # Connect to the database to check if the email exists
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        
        if user:
            # Generate a unique token for the recovery link
            token = secrets.token_urlsafe(16)  # Generate a random token
            
            # Create the recovery URL
            recovery_link = url_for('forgot_password', token=token, _external=True)
            
            # Send the recovery email with the link
            msg = Message('Password Recovery Link', recipients=[email],sender='hifidelivery213@gmail.com')
            msg.body = f'Click the link to reset your password: {recovery_link}'
            mail.send(msg)
            
            # Redirect to the confirmation page (forgot.html)
            return render_template('recovery.html', message="A recovery link has been sent to your email address.")
        else:
            conn.close()
            return render_template('recovery.html', error="Invalid email address. Please try again.")
    
    return render_template('recovery.html')

# Route to show the forgot password page when clicking the recovery link
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    token = request.args.get('token')  # Get the token from the URL
    if request.method == 'POST':
        identifier = request.form.get('identifier')  # Can be email or username
        new_password = request.form.get('new_password')
        re_new_password = request.form.get('re_new_password')

        if new_password != re_new_password:
            flash('Passwords do not match. Please try again.', 'error')
            return redirect(url_for('forgot_password', token=token))

        # Hash the new password before storing it (optional but recommended for security)
        hashed_password = new_password  # Replace with hash function if needed

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        try:
            # Update password for the user identified by email or username
            cursor.execute(
                "UPDATE users SET password=? WHERE email=? OR username=?", 
                (hashed_password, identifier, identifier)
            )
            conn.commit()

            # Check if any row was updated
            if cursor.rowcount == 0:
                flash('No user found with the provided email or username.', 'error')
                return redirect(url_for('forgot_password', token=token))

            flash('Password reset successful. Please log in with your new password.', 'success')
            return redirect(url_for('login'))  # Replace 'login' with your login route
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
            return redirect(url_for('forgot_password', token=token))
        finally:
            conn.close()

    return render_template('forgot.html')  # The page where users reset their password
#forgot password end
@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/delivery')
def delivery():
    return render_template('deliveryagent.html')

@app.route('/deliverystatus')
def delivery_status():
    return render_template('deliverystatus.html')

@app.route('/deliveryissue')
def delivery_issue():
    return render_template('deliveryissue.html')

# @app.route('/recovery')
# def recovery():
#     return render_template('recovery.html')

@app.route('/update_details', methods=['GET', 'POST'])
def update_details():
    if 'user_id' not in session:
        flash('Please log in to update your details.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']

    if request.method == 'POST':
        new_username = request.form['username']
        new_email = request.form['email']
        new_role = request.form['role']
        new_location = request.form['location']
        new_contact = request.form['contact']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE users
                SET username = ?, email = ?, role = ?, location = ?, contact = ?
                WHERE id = ?
            ''', (new_username, new_email, new_role, new_location, new_contact, user_id))
            conn.commit()
            flash('Details updated successfully!', 'success')

            # Update session values
            session['username'] = new_username
            session['email'] = new_email
            session['role'] = new_role
            session['location'] = new_location
            session['contact'] = new_contact

            return redirect(url_for('start'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists. Please choose another.', 'danger')
        finally:
            conn.close()

    # Fetch current user details for the form
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT username, email, role, location, contact FROM users WHERE id = ?', (user_id,))
    user_details = cursor.fetchone()
    conn.close()

    return render_template('profile.html', user={
        'username': user_details[0],
        'email': user_details[1],
        'role': user_details[2],
        'location': user_details[3],
        'contact': user_details[4]
    })

@app.route('/viewprofile')
def viewprofile():
    if 'user_id' not in session:
        flash('Please log in to access the dashboard.', 'danger')
        return redirect(url_for('login'))

    user_details = {
        'username': session.get('username'),
        'email': session.get('email'),
        'role': session.get('role'),
        'location': session.get('location'),
        'contact': session.get('contact'),
    }

    return render_template('viewprofile.html', user=user_details)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

# @app.route('/forgot_password', methods=['GET', 'POST'])
# def forgot_password():
#     if request.method == 'POST':
#         identifier = request.form.get('identifier')
#         new_password = request.form.get('new_password')
#         re_new_password = request.form.get('re_new_password')
#         print(f'identifier:{identifier}\nnew_password:{new_password}\nre-new-password:{re_new_password}')
#         if new_password != re_new_password:
#             flash('Passwords do not match. Please try again.', 'error')
#             return redirect(url_for('forgot_password'))
#         flash('Password reset successful. Please log in with your new password.', 'success')
#         return redirect(url_for('start'))

#     return render_template(url_for('forgot'))

@app.route('/admin/approvals', methods=['GET'])
def admin_approvals():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Access restricted to administrators.', 'danger')
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, email, role, contact FROM users WHERE approved = 0')
    pending_users = cursor.fetchall()
    conn.close()

    return render_template('approvals.html', pending_users=pending_users)

@app.route('/admin/approve_user/<int:user_id>', methods=['POST'])
def approve_user(user_id):
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Access restricted to administrators.', 'danger')
        return redirect(url_for('login'))

    action = request.form['action']  # 'approve' or 'reject'
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    if action == 'approve':
        cursor.execute('UPDATE users SET approved = 1 WHERE id = ?', (user_id,))
        flash('User approved successfully.', 'success')
    elif action == 'reject':
        cursor.execute('UPDATE users SET approved = -1 WHERE id = ?', (user_id,))
        flash('User rejected successfully.', 'danger')
    conn.commit()
    conn.close()

    return redirect(url_for('admin_approvals'))

@app.route('/submit_agent_issue',methods=['POST'])
def submit_agent_issue():
    if request.method == 'POST':
        agent_name = request.form['agent_name']
        order_id = request.form['order_id']
        issue_type = request.form['issue_type']
        details = request.form['details']
        print(agent_name,order_id,issue_type,details)

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO Delivery_Agent_Report(Agent, OrderId, IssueType,IssueDetails)
                    VALUES (?, ?, ?, ?)
                """, (agent_name,order_id,issue_type,details))
                conn.commit()
                print("Done 1")

            flash('Reported successfully', 'success')
            return redirect(url_for('delivery'))
        except sqlite3.OperationalError:
            flash('Database is currently locked. Please try again later.', 'danger')
            return redirect(url_for('delivery_issue'))
    



if __name__ == '__main__':
    app.run(debug=True)