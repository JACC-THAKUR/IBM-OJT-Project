from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, session
# from emotion import analyze_sentiment_vader, analyze_sentiment_bert, recommend_coping_mechanisms # type: ignore
import numpy as np
import pandas as pd
import pickle
import joblib 
from flask_mysqldb import MySQL
from MySQLdb._exceptions import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
import logging
import os
from werkzeug.utils import secure_filename
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import random
import string
import smtplib
# from chatbot import ChatBot 
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
# from dotenv import load_dotenv
import google.generativeai as genai

# # Load environment variables
# load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler(),  # Log to console
                        logging.FileHandler('app.log')  # Log to file
                    ])
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'AIzaSyBfrXwYPsVklt3edTC5a3-fFIntv3MG7SA')  # Use a secure key
# MySQL configuration
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'flask_crud_db'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_PORT'] = 3306  # Default MySQL port

mysql = MySQL(app)




# Configure the Generative AI model
api_key = os.getenv("GENAI_API_KEY")  # Use environment variable for security
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-pro")
chat = model.start_chat(history=[])

def get_gemini_response(question):
    try:
        response = chat.send_message(question, stream=True)
        return response
    except genai.types.generation_types.BrokenResponseError:
        logger.error("Encountered BrokenResponseError. Retrying...")
        chat.rewind()
        response = chat.send_message(question, stream=True)
        return response
    except Exception as e:
        logger.exception("Unexpected error occurred while getting response.")
        raise e

@app.route('/bot', methods=['GET', 'POST'])
def bot():
    if not session.get('user_id'):
        flash('Please login first', 'danger')
        return redirect(url_for('login'))
    
    if 'chat_history' not in session:
        session['chat_history'] = []
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_image = session.get('user_image')


    if request.method == 'POST':
        user_input = request.form['input']
        if user_input:
            try:
                response = get_gemini_response(user_input)
                session['chat_history'].append(("You", user_input))
                response_texts = [chunk.text for chunk in response]
                session['chat_history'].append(("Bot", " ".join(response_texts)))
                session.modified = True  # Mark the session as modified to save changes
            except Exception as e:
                logger.exception("Error during response generation:")
                session['chat_history'].append(("Bot", "Sorry, I encountered an error. Please try again."))

            return redirect(url_for('bot'))

    return render_template('Service/bot.html',user_name=user_name,
                            user_email=user_email,
                              user_image=user_image, chat_history=session.get('chat_history', []))

#========================================================Email Code send otp Password and token===========================================================
#========================================================Email Code send otp Password token===========================================================

def generate_otp_token(length=6):
    """
    Generate a random OTP token of the given length.
    """
    characters = string.digits  # OTP consists of digits only
    otp_token = ''.join(random.choice(characters) for _ in range(length))
    return otp_token



def send_email(receiver_email, username=None, message_type=None, password=None, otp_token=None, contact_message=None, appointment_details=None):
    sender_email = "healthenginewithaiassistancee@gmail.com"
    sender_password = "oaig owrp uqxt xzxf"

    logo_path = os.path.join(app.root_path, 'static', 'img', 'logo.png')
    logo_cid = 'logo_cid'

    if message_type == 'account_creation':
        subject = "Your Account Details"
        body = f"""
        <html>
        <body>
            <img src="cid:{logo_cid}" alt="Health Engine Logo" style="width:150px;height:50px;"><br>
            <p>Dear {username},</p>
            <p>Your account has been created.</p>
            <p><b>Username:</b> {username}<br>
            <b>Password:</b> {password}</p>
            <p>Please log in and change your password after your first login to ensure your account's security.</p>
            <p>Welcome to Health Engine! We are excited to have you on board. If you have any questions, feel free to contact us.</p>
            <p>Best regards,<br>Your Health Engine Team</p>
        </body>
        </html>
        """
    elif message_type == 'otp_code':
        subject = "Your OTP Code"
        body = f"""
        <html>
        <body>
            <img src="cid:{logo_cid}" alt="Health Engine Logo" style="width:150px;height:50px;"><br>
            <p>Dear {username},</p>
            <p>Your OTP code for password reset is: <b>{otp_token}</b></p>
            <p>If you did not request a password reset, please ignore this email.</p>
            <p>Best regards,<br>Your Health Engine Team</p>
        </body>
        </html>
        """
    elif message_type == 'contact_form':
        subject = "Contact Form Message"
        body = f"""
        <html>
        <body>
            <img src="cid:{logo_cid}" alt="Health Engine Logo" style="width:150px;height:50px;"><br>
            <p>Message from contact form:</p>
            <p>{contact_message}</p>
            <p>Thank you for reaching out to us. We will get back to you shortly.</p>
            <p>Best regards,<br>Your Health Engine Team</p>
        </body>
        </html>
        """
    elif message_type == 'appointment_notification':
        subject = "Appointment Update"
        body = f"""
        <html>
        <body>
            <img src="cid:{logo_cid}" alt="Health Engine Logo" style="width:150px;height:50px;"><br>
            <p>Dear {username},</p>
            <p>{appointment_details}</p>
            <p>If you have any questions or need to reschedule, please contact us.</p>
            <p>Best regards,<br>Your Health Engine Team</p>
        </body>
        </html>
        """
    else:
        raise ValueError("Invalid message_type. Use 'account_creation', 'otp_code', 'contact_form', or 'appointment_notification'.")

    msg = MIMEMultipart('related')
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'html'))

    try:
        with open(logo_path, 'rb') as logo:
            logo_image = MIMEImage(logo.read())
            logo_image.add_header('Content-ID', f'<{logo_cid}>')
            msg.attach(logo_image)
    except Exception as e:
        logging.error("Failed to attach logo image: %s", e)

    try:
        logging.debug("Attempting to send %s email...", message_type)
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        logging.info("%s email sent successfully to %s", message_type, receiver_email)
    except Exception as e:
        logging.error("Failed to send %s email to %s: %s", message_type, receiver_email, e)


#========================================================Upload File Like Image Path===========================================================
#========================================================Upload File Like Image Path===========================================================
# Ensure the upload folder exists
UPLOAD_FOLDER = 'static/profile_images'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#========================================================Home Page Routes for user doctor and admin===========================================================
#========================================================Home Page Routes for User doctor and admin===========================================================

@app.route("/")
def index():
    if 'user_id' in session:
        if session.get('is_super_admin'):
            return redirect(url_for('super_admin_dashboard'))
        elif session.get('is_admin'):
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('dashboard'))
    return render_template("index.html")


#========================================================Login Routes===========================================================
#========================================================Login Routes===========================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        if session.get('is_super_admin'):
            return redirect(url_for('super_admin_dashboard'))
        elif session.get('is_admin'):
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('dashboard'))

    if request.method == 'POST':
        login_input = request.form['login_input']
        password = request.form['password']

        conn = mysql.connection
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE (name = %s OR email = %s)", (login_input, login_input))
        user = cursor.fetchone()
        cursor.close()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['user_email'] = user[2]
            session['user_height'] = user[6]
            session['user_weight'] = user[7]
            session['user_image'] = user[8]

            if user[13]:  # Assuming column index 13 is is_super_admin
                session['is_super_admin'] = True
                flash('Super Admin login successful!', 'success')
                return redirect(url_for('super_admin_dashboard'))
            elif user[4]:  # Assuming column index 4 is is_admin
                session['is_admin'] = True
                flash('Admin login successful!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                session['is_admin'] = False
                session['is_super_admin'] = False
                flash('User login successful!', 'success')
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid username/email or password', 'danger')

    return render_template('Auth/login.html')

#========================================================After login Dashbord Route===========================================================
#========================================================After login Dashbord Route===========================================================
@app.route('/dashboard')
def dashboard():
    if not session.get('user_id'):
        flash('Please login first', 'danger')
        return redirect(url_for('login'))
    
    # Check if the user is an admin and redirect to the admin dashboard if true
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))
    user_id =session.get('user_id')
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_height = session.get('user_height')
    user_weight = session.get('user_weight')
    user_image = session.get('user_image')

    logging.debug(f"User Dashboard - User Name: {user_name}, User Email: {user_email}, User Height: {user_height}, User Weight: {user_weight}, User Image: {user_image}")

    return render_template('index.html',user_id=user_id, user_name=user_name, user_email=user_email, user_height=user_height, user_weight=user_weight, user_image=user_image)



#========================================================Admin Dashboard/Doctor Route===========================================================
#========================================================Admin Dashboard/Doctor Route===========================================================
# @app.route('/bord')
# def bord():
#     if not session.get('is_admin'):
#         flash('Access denied!', 'danger')
#         return redirect(url_for('login'))

#     user_name = session.get('user_name')
#     user_email = session.get('user_email')
#     user_height = session.get('user_height')
#     user_weight = session.get('user_weight')
#     user_image = session.get('user_image') or 'default_image.jpg'  # Provide a default image if None

#     # Fetch the patients added by the current admin
#     conn = mysql.connection
#     cursor = conn.cursor()

#     try:
#         cursor.execute("""
#             SELECT u.id, u.name, u.email, u.height, u.weight, u.image, u.patient_id, h.age, h.gender, h.activity, h.diet, h.smoking, h.alcohol, h.conditions, h.medications, h.family_history, h.sleep, h.stress
#             FROM users u
#             LEFT JOIN user_health_info h ON u.id = h.user_id
#             WHERE u.user_type = 'user' AND u.added_by = %s
#         """, (session['user_id'],))
#         patients = cursor.fetchall()
#     except Exception as e:
#         flash(f'Error fetching patients: {str(e)}', 'danger')
#         return redirect(url_for('login'))
#     finally:
#         cursor.close()

#     return render_template('Doctors/bord.html',
#                            user_name=user_name, user_email=user_email,
#                            user_height=user_height, user_weight=user_weight,
#                            user_image=user_image, patients=patients)

                              
@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('is_admin'):
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))

    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_height = session.get('user_height')
    user_weight = session.get('user_weight')
    user_image = session.get('user_image') or 'default_image.jpg'  # Default image if None

    conn = mysql.connection
    cursor = conn.cursor()

    try:
        # Fetch patient data
        cursor.execute("""
            SELECT u.id, u.name, u.email, u.height, u.weight, u.image, h.age, h.gender, h.activity, h.diet, h.smoking, h.alcohol, h.conditions, h.medications, h.family_history, h.sleep, h.stress
            FROM users u
            LEFT JOIN user_health_info h ON u.id = h.user_id
            WHERE u.user_type = 'user' AND u.added_by = %s
        """, (session['user_id'],))
        patients = cursor.fetchall()

        # Fetch monthly new patients data
        cursor.execute("""
            SELECT DATE_FORMAT(created_at, '%Y-%m') AS month, COUNT(*) AS count
            FROM users
            WHERE user_type = 'user' AND created_at >= DATE_SUB(NOW(), INTERVAL 1 YEAR)
            GROUP BY month
            ORDER BY month
        """)
        monthly_new_patients = cursor.fetchall()

        # Prepare data for the chart
        months = [row[0] for row in monthly_new_patients]
        counts = [row[1] for row in monthly_new_patients]

        # Fetch additional stats
        cursor.execute("SELECT COUNT(*) FROM users WHERE user_type='user'")
        total_patients = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE user_type='user' AND created_at >= DATE_SUB(NOW(), INTERVAL 1 MONTH)")
        new_patients = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM appointments")
        total_appointments = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM appointments WHERE status='pending'")
        pending_appointments = cursor.fetchone()[0]

        # Make sure to define recent_activities if it's used in the template
        recent_activities = {
            'labels': months,
            'data': counts,
        }

    except Exception as e:
        flash(f'Error fetching data: {str(e)}', 'danger')
        return redirect(url_for('login'))
    finally:
        cursor.close()

    return render_template('/Doctors/admin_dashboard.html',
                           user_name=user_name, user_email=user_email,
                           user_height=user_height, user_weight=user_weight,
                           user_image=user_image, patients=patients,
                           recent_activities=recent_activities,  # Ensure this is included
                           total_patients=total_patients,
                           new_patients=new_patients,
                           total_appointments=total_appointments,
                           pending_appointments=pending_appointments)

#========================================================Super Admin/main Admin Route===========================================================
#========================================================Super Admin/main Admin Route===========================================================
@app.route('/superbord')
def superbord():
    if 'is_super_admin' not in session or not session['is_super_admin']:
        flash('Unauthorized access. Only super admins can access this page.', 'danger')
        return redirect(url_for('index'))
    
    conn = mysql.connection
    cursor = conn.cursor()

    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_image = session.get('user_image') or 'default_image.jpg'
    

    

    # Fetch all doctors
    cursor.execute("SELECT * FROM users WHERE user_type='doctor'")
    doctors = cursor.fetchall()

    # Fetch all users
    cursor.execute("SELECT * FROM users WHERE user_type='user'")
    users = cursor.fetchall()

    # Fetch the number of doctors and users
    num_doctors = len(doctors)
    num_users = len(users)

    # Fetch specializations and their counts
    cursor.execute("""
        SELECT specialization, COUNT(*) 
        FROM users 
        WHERE user_type = 'doctor' 
        GROUP BY specialization
    """)
    specializations = cursor.fetchall()

    cursor.close()
    

    return render_template(
        'SuperAdmin/superbord.html',
        doctors=doctors,
        users=users,
        num_doctors=num_doctors,
        num_users=num_users,
        specializations=specializations,
        user_name=user_name,
        user_image=user_image,
        user_email=user_email
    )


@app.route('/super_admin_dashboard')
def super_admin_dashboard():
    if 'is_super_admin' not in session or not session['is_super_admin']:
        flash('Unauthorized access. Only super admins can access this page.', 'danger')
        return redirect(url_for('index'))

    conn = mysql.connection
    cursor = conn.cursor()

    # Fetch all doctors
    cursor.execute("SELECT * FROM users WHERE user_type='doctor'")
    doctors = cursor.fetchall()

    # Fetch all users
    cursor.execute("SELECT * FROM users WHERE user_type='user'")
    users = cursor.fetchall()

    # Fetch the number of doctors and users
    num_doctors = len(doctors)
    num_users = len(users)

    # Fetch specializations and their counts
    cursor.execute("""
        SELECT specialization, COUNT(*) 
        FROM users 
        WHERE user_type = 'doctor' 
        GROUP BY specialization
    """)
    specializations = cursor.fetchall()

    cursor.close()

    return render_template(
        'SuperAdmin/super_admin_dashboard.html',
        doctors=doctors,
        users=users,
        num_doctors=num_doctors,
        num_users=num_users,
        specializations=specializations
    )






#========================================================SignUp Route===========================================================
#========================================================SignUP Route===========================================================
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if session.get('user_id'):
        if session.get('is_super_admin'):
            return redirect(url_for('super_admin_dashboard'))
        elif session.get('is_admin'):
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        conn = mysql.connection
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", 
                           (name, email, hashed_password))
            conn.commit()
            flash('Sign up successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except IntegrityError:
            flash('Email already exists. Please use a different email.', 'danger')
            conn.rollback()
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            conn.rollback()
        finally:
            cursor.close()
    return render_template('/Auth/signup.html')


#========================================================Forget Password Route===========================================================
#========================================================ForgetPassword Route===========================================================
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')  # Use get() to avoid KeyError
        
        conn = mysql.connection
        cursor = conn.cursor()
        
        # Check if the email exists in the database
        cursor.execute("SELECT name FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if user:
            username = user[0]
            otp_token = generate_otp_token()
            
            # Insert OTP token into the database
            cursor.execute("INSERT INTO otp_tokens (email, token) VALUES (%s, %s)", (email, otp_token))
            conn.commit()
            
            # Send the OTP code to the user's email
            send_email(email, username, 'otp_code', otp_token=otp_token)
            
            flash('OTP code sent to your email.', 'success')
            return redirect(url_for('verify_otp', email=email))  # Pass email as a query parameter
        else:
            flash('Email not found.', 'danger')
    
    return render_template('Auth/forgot_password.html')


#========================================================Verify OTP Route===========================================================
#========================================================Verify OTP Route===========================================================

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    email = request.args.get('email')  # Get email from the query string

    if request.method == 'POST':
        otp_token = request.form.get('otp_token')
        new_password = request.form.get('new_password')

        if not otp_token or not new_password:
            flash('OTP token and new password are required.', 'danger')
            return redirect(url_for('verify_otp', email=email))  # Redirect to the same page to show the form

        conn = mysql.connection
        cursor = conn.cursor()
        
        # Verify OTP token
        cursor.execute("SELECT * FROM otp_tokens WHERE email = %s AND token = %s", (email, otp_token))
        token_record = cursor.fetchone()
        
        if token_record:
            hashed_password = generate_password_hash(new_password)
            cursor.execute("UPDATE users SET password = %s WHERE email = %s", (hashed_password, email))
            conn.commit()
            
            # Remove the OTP token from the database
            cursor.execute("DELETE FROM otp_tokens WHERE email = %s", (email,))
            conn.commit()
            
            flash('Password updated successfully.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid OTP code.', 'danger')
    
    return render_template('/Auth/verify_otp.html')


#========================================================Update Password Route===========================================================
#========================================================Update Password Route===========================================================
@app.route('/update_password', methods=['GET', 'POST'])
def update_password():
    if not session.get('user_id'):
        flash('You need to log in to access this page.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_new_password = request.form.get('confirm_new_password')

        # Validate form data
        if not current_password or not new_password or not confirm_new_password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('update_password'))

        if new_password != confirm_new_password:
            flash('New passwords do not match.', 'danger')
            return redirect(url_for('update_password'))

        conn = mysql.connection
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM users WHERE id = %s', (session['user_id'],))
        user = cursor.fetchone()
        cursor.close()

        if user and check_password_hash(user[0], current_password):
            hashed_new_password = generate_password_hash(new_password)
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET password = %s WHERE id = %s', (hashed_new_password, session['user_id']))
            conn.commit()
            cursor.close()
            flash('Password updated successfully!', 'success')
            return redirect(url_for('profile'))  # Redirect to the user's profile page or another appropriate page
        else:
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('update_password'))

    return render_template('/Auth/update_password.html')


#========================================================Logout Route==============================================================
#========================================================Logout Route==============================================================
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))



#========================================================Direct Add Doctor/Admin Route===========================================================
#========================================================Direct Add Doctor/Admin Route===========================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Check if the user is logged in and is a super admin
    if 'is_super_admin' not in session or not session['is_super_admin']:
        flash('Unauthorized access. Only super admins can access this page.', 'danger')
        return redirect(url_for('index'))  # Redirect to home or another page for non-super admin users
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']
        is_admin = 'is_admin' in request.form
        specialization = request.form.get('specialization', '')  # Default to empty string if not present
        qualifications = request.form.get('qualifications', '')  # Default to empty string if not present
        experience = request.form.get('experience', 0)  # Default to 0 if not present
        phone = request.form.get('phone', '')  # Default to empty string if not present
        clinic_address = request.form.get('clinic_address', '')  # Default to empty string if not present

        hashed_password = generate_password_hash(password)

        conn = mysql.connection
        cursor = conn.cursor()
        if user_type == 'doctor':
            cursor.execute("""
                INSERT INTO users (name, email, password, is_admin, user_type, specialization, qualifications, experience, phone, clinic_address) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (username, email, hashed_password, is_admin, user_type, specialization, qualifications, experience, phone, clinic_address))
        else:
            cursor.execute("""
                INSERT INTO users (name, email, password, is_admin, user_type) 
                VALUES (%s, %s, %s, %s, %s)
                """, (username, email, hashed_password, is_admin, user_type))
        conn.commit()
        cursor.close()

        flash('Registration successful!', 'success')
        return redirect(url_for('register'))  # Redirect to the register page to register more users
    return render_template('SuperAdmin/register.html')



#========================================================Profile Page for All Route===========================================================
#========================================================Profile Page for All Route===========================================================
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if not session.get('user_id'):
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Handle the profile update form submission
        name = request.form.get('name')
        email = request.form.get('email')
        height = request.form.get('height')
        weight = request.form.get('weight')
        age = request.form.get('age')
        gender = request.form.get('gender')
        activity = request.form.get('activity')
        diet = request.form.get('diet')
        smoking = request.form.get('smoking')
        alcohol = request.form.get('alcohol')
        conditions = request.form.get('conditions')
        medications = request.form.get('medications')
        family_history = request.form.get('family_history')
        sleep = request.form.get('sleep')
        stress = request.form.get('stress')

        image = None
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image = filename

        conn = mysql.connection
        cursor = conn.cursor()
        if image:
            cursor.execute("""
                UPDATE users 
                SET name = %s, email = %s, height = %s, weight = %s, image = %s 
                WHERE id = %s
            """, (name, email, height, weight, image, session['user_id']))
        else:
            cursor.execute("""
                UPDATE users 
                SET name = %s, email = %s, height = %s, weight = %s 
                WHERE id = %s
            """, (name, email, height, weight, session['user_id']))

        cursor.execute("""
            INSERT INTO user_health_info (user_id, height, weight, age, gender, activity, diet, smoking, alcohol, conditions, medications, family_history, sleep, stress)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            height = VALUES(height),
            weight = VALUES(weight),
            age = VALUES(age),
            gender = VALUES(gender),
            activity = VALUES(activity),
            diet = VALUES(diet),
            smoking = VALUES(smoking),
            alcohol = VALUES(alcohol),
            conditions = VALUES(conditions),
            medications = VALUES(medications),
            family_history = VALUES(family_history),
            sleep = VALUES(sleep),
            stress = VALUES(stress)
        """, (session['user_id'], height, weight, age, gender, activity, diet, smoking, alcohol, conditions, medications, family_history, sleep, stress))

        conn.commit()
        cursor.close()

        # Update the session data with the new profile information
        session['user_name'] = name
        session['user_email'] = email
        session['user_height'] = height
        session['user_weight'] = weight
        session['user_image'] = image if image else session['user_image']

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    else:
        # Handle the profile view
        conn = mysql.connection
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.name, u.email, u.height, u.weight, u.image,
                   h.height, h.weight, h.age, h.gender, h.activity, h.diet,
                   h.smoking, h.alcohol, h.conditions, h.medications, h.family_history,
                   h.sleep, h.stress
            FROM users u
            LEFT JOIN user_health_info h ON u.id = h.user_id
            WHERE u.id = %s
        """, (session['user_id'],))
        user = cursor.fetchone()
        cursor.close()

        if user:
            user_data = {
                'id': user[0],
                'name': user[1],
                'email': user[2],
                'height': user[3],
                'weight': user[4],
                'image': user[5] if user[5] else 'default.jpg',  # Default image if user has none
                'health_info': {
                    'height': user[6],
                    'weight': user[7],
                    'age': user[8],
                    'gender': user[9],
                    'activity': user[10],
                    'diet': user[11],
                    'smoking': user[12],
                    'alcohol': user[13],
                    'conditions': user[14],
                    'medications': user[15],
                    'family_history': user[16],
                    'sleep': user[17],
                    'stress': user[18],
                }
            }

            # Update the session data with the user's profile information
            session['user_name'] = user_data['name']
            session['user_email'] = user_data['email']
            session['user_height'] = user_data['height']
            session['user_weight'] = user_data['weight']
            session['user_image'] = user_data['image']

            return render_template('users/profile.html', user=user_data)
        else:
            flash('User not found.', 'danger')
            return redirect(url_for('login'))
        
#=-================================================Doctore profile ======================================================================
#===================================================Docotre Profile =================================================================        

@app.route('/doctorprofile', methods=['GET', 'POST'])
def doctorprofile():
    
    if not session.get('is_admin'):
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))
    
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_image = session.get('user_image') or 'default_image.jpg'  # Default image if None

  
    
    if request.method == 'POST':
        # Handle the profile update form submission
        name = request.form.get('name')
        email = request.form.get('email')
        height = request.form.get('height')
        weight = request.form.get('weight')
        age = request.form.get('age')
        gender = request.form.get('gender')
        activity = request.form.get('activity')
        diet = request.form.get('diet')
        smoking = request.form.get('smoking')
        alcohol = request.form.get('alcohol')
        conditions = request.form.get('conditions')
        medications = request.form.get('medications')
        family_history = request.form.get('family_history')
        sleep = request.form.get('sleep')
        stress = request.form.get('stress')

        image = None
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image = filename

        conn = mysql.connection
        cursor = conn.cursor()
        if image:
            cursor.execute("""
                UPDATE users 
                SET name = %s, email = %s, height = %s, weight = %s, image = %s 
                WHERE id = %s
            """, (name, email, height, weight, image, session['user_id']))
        else:
            cursor.execute("""
                UPDATE users 
                SET name = %s, email = %s, height = %s, weight = %s 
                WHERE id = %s
            """, (name, email, height, weight, session['user_id']))

        cursor.execute("""
            INSERT INTO user_health_info (user_id, height, weight, age, gender, activity, diet, smoking, alcohol, conditions, medications, family_history, sleep, stress)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            height = VALUES(height),
            weight = VALUES(weight),
            age = VALUES(age),
            gender = VALUES(gender),
            activity = VALUES(activity),
            diet = VALUES(diet),
            smoking = VALUES(smoking),
            alcohol = VALUES(alcohol),
            conditions = VALUES(conditions),
            medications = VALUES(medications),
            family_history = VALUES(family_history),
            sleep = VALUES(sleep),
            stress = VALUES(stress)
        """, (session['user_id'], height, weight, age, gender, activity, diet, smoking, alcohol, conditions, medications, family_history, sleep, stress))

        conn.commit()
        cursor.close()

        # Update the session data with the new profile information
        session['user_name'] = name
        session['user_email'] = email
        session['user_height'] = height
        session['user_weight'] = weight
        session['user_image'] = image if image else session['user_image']

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('doctorprofile'))

    else:
        # Handle the profile view
        conn = mysql.connection
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.name, u.email, u.height, u.weight, u.image,
                   h.height, h.weight, h.age, h.gender, h.activity, h.diet,
                   h.smoking, h.alcohol, h.conditions, h.medications, h.family_history,
                   h.sleep, h.stress
            FROM users u
            LEFT JOIN user_health_info h ON u.id = h.user_id
            WHERE u.id = %s
        """, (session['user_id'],))
        user = cursor.fetchone()
        cursor.close()

        if user:
            user_data = {
                'id': user[0],
                'name': user[1],
                'email': user[2],
                'height': user[3],
                'weight': user[4],
                'image': user[5] if user[5] else 'default.jpg',  # Default image if user has none
                'health_info': {
                    'height': user[6],
                    'weight': user[7],
                    'age': user[8],
                    'gender': user[9],
                    'activity': user[10],
                    'diet': user[11],
                    'smoking': user[12],
                    'alcohol': user[13],
                    'conditions': user[14],
                    'medications': user[15],
                    'family_history': user[16],
                    'sleep': user[17],
                    'stress': user[18],
                }
            }

            # Update the session data with the user's profile information
            session['user_name'] = user_data['name']
            session['user_email'] = user_data['email']
            session['user_height'] = user_data['height']
            session['user_weight'] = user_data['weight']
            session['user_image'] = user_data['image']

            return render_template('Doctors/doctorprofile.html', user=user_data,
                                   user_name=user_name,user_email=user_email,user_image=user_image)
        else:
            flash('User not found.', 'danger')
            return redirect(url_for('login'))     


#========================================================Health Data Route===========================================================
#========================================================Health Data Route===========================================================
# @app.route('/user/<int:user_id>')
# def user_health(user_id):
#     connection = mysql.connection
#     cursor = connection.cursor()
    
#     # Fetch user health data
#     cursor.execute("""
#         SELECT height, weight, age, gender, activity, diet, smoking, alcohol, conditions, medications, family_history, sleep, stress 
#         FROM user_health_info WHERE user_id = %s
#     """, (user_id,))
#     health_data = cursor.fetchall()
    
#     # Fetch user name and image
#     cursor.execute("""
#         SELECT name, image FROM users WHERE id = %s
#     """, (user_id,))
#     user_info = cursor.fetchone()
    
#     cursor.close()

#     # Convert health data into a format suitable for the frontend
#     health_data = {
#         'height': [row[0] for row in health_data],
#         'weight': [row[1] for row in health_data],
#         'age': [row[2] for row in health_data],
#         'gender': [row[3] for row in health_data],
#         'activity': [row[4] for row in health_data],
#         'diet': [row[5] for row in health_data],
#         'smoking': [row[6] for row in health_data],
#         'alcohol': [row[7] for row in health_data],
#         'conditions': [row[8] for row in health_data],
#         'medications': [row[9] for row in health_data],
#         'family_history': [row[10] for row in health_data],
#         'sleep': [row[11] for row in health_data],
#         'stress': [row[12] for row in health_data]
#     }

#     # Prepare user data
#     user_data = {
#         'name': user_info[0],
#         'image': user_info[1]
#     }

#     return render_template('/users/health_data.html', health_data=health_data, user_data=user_data)

@app.route('/user/<int:user_id>')
def user_dashboard(user_id):
    connection = mysql.connection
    cursor = connection.cursor()
    
    # Fetch user health data
    cursor.execute("""
        SELECT height, weight, age, gender, activity, diet, smoking, alcohol, conditions, medications, family_history, sleep, stress 
        FROM user_health_info WHERE user_id = %s
    """, (user_id,))
    health_data = cursor.fetchone()
    
    # Fetch user name and image
    cursor.execute("""
        SELECT name, image FROM users WHERE id = %s
    """, (user_id,))
    user_info = cursor.fetchone()
    
    cursor.close()

    # Define fixed example data (for demonstration purposes)
    example_data = {
        'years': ['2020', '2021', '2022', '2023'],
        'weights': [70, 72, 74, 76],  # Example weights
        'activity': [3, 4],  # Example activity levels
        'diet': [4, 5],  # Example diet levels
        'stress': [5, 6, 4, 7],  # Example stress levels
    }

    # Prepare health data
    health_data = {
        'height': health_data[0],
        'weight': health_data[1],
        'age': health_data[2],
        'gender': health_data[3],
        'activity': health_data[4],
        'diet': health_data[5],
        'smoking': health_data[6],
        'alcohol': health_data[7],
        'conditions': health_data[8],
        'medications': health_data[9],
        'family_history': health_data[10],
        'sleep': health_data[11],
        'stress': health_data[12]
    }

    user_data = {
        'name': user_info[0],
        'image': user_info[1]
    }

    # Suggest health tips based on the user's data
    health_tips = []
    if health_data['smoking'] == 'Yes':
        health_tips.append("Consider quitting smoking to improve your overall health.")
    else:
        health_tips.append("Maintain a smoke-free lifestyle for better lung health.")

    if health_data['alcohol'] == 'Yes':
        health_tips.append("Limit alcohol consumption to maintain liver health.")
    else:
        health_tips.append("Continue avoiding excessive alcohol consumption to protect your liver.")

    if health_data['sleep'] < 7:
        health_tips.append("Ensure you get at least 7-8 hours of sleep each night.")
    else:
        health_tips.append("Maintain your healthy sleep routine to keep your energy levels up.")

    if health_data['activity'] == 'Low':
        health_tips.append("Increase your physical activity to at least 30 minutes a day.")
    else:
        health_tips.append("Keep up your active lifestyle to stay fit and healthy.")

    return render_template('/users/health_data.html', health_data=health_data, user_data=user_data, health_tips=health_tips, example_data=example_data)


#========================================================Add Patient Admin Route===========================================================
#========================================================Add Patient Admin Route===========================================================

@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if not session.get('is_admin'):
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        user_type = 'user'  # Default user_type is 'user'

        if not name or not email or not phone:
            flash('Name, email, and phone are required.', 'danger')
            return redirect(url_for('add_patient'))

        username_part = email.split('@')[0]
        simple_password = f"{username_part}@123"
        hashed_password = generate_password_hash(simple_password)

        try:
            conn = mysql.connection
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (name, email, phone, password, user_type, added_by, is_patient)
                VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            """, (name, email, phone, hashed_password, user_type, session['user_id']))
            conn.commit()
            cursor.close()

            # Send the password to the new patient via email
            send_email(email, name, 'account_creation', password=simple_password)

            flash('Patient added successfully! An email has been sent with the password.', 'success')
            return redirect(url_for('add_patient'))
        except Exception as e:
            flash(f'An error occurred while adding the patient: {str(e)}', 'danger')
            return redirect(url_for('add_patient'))

    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_image = session.get('user_image')

    # Fetch the patients added by the current admin
    try:
        conn = mysql.connection
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, email, phone, image
            FROM users
            WHERE is_patient = TRUE AND added_by = %s
        """, (session['user_id'],))
        patients = cursor.fetchall()
        cursor.close()
    except Exception as e:
        flash(f'An error occurred while fetching patients: {str(e)}', 'danger')
        patients = []

    return render_template('Doctors/add_patient.html', user_name=user_name, user_email=user_email, 
                           user_image=user_image, patients=patients)



#========================================================View Patient Admin Route===========================================================
#========================================================View Patient Admin Route===========================================================
@app.route('/view_patient/<int:patient_id>', methods=['GET'])
def view_patient(patient_id):
    if not session.get('is_admin'):
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))
    
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_image = session.get('user_image') or 'default_image.jpg'  # Provide a default image if None

    

    conn = mysql.connection
    cursor = conn.cursor()

    try:
        # Fetch patient basic information
        cursor.execute("""
            SELECT id, name, email, height, weight, image
            FROM users
            WHERE id = %s AND is_patient = TRUE
        """, (patient_id,))
        patient = cursor.fetchone()

        if not patient:
            flash('Patient not found!', 'danger')
            return redirect(url_for('admin_dashboard'))

        # Fetch patient health information
        cursor.execute("""
            SELECT height, weight, age, gender, activity, diet, smoking, alcohol, conditions, medications, family_history, sleep, stress
            FROM user_health_info
            WHERE user_id = %s
        """, (patient_id,))
        health_info = cursor.fetchone()
    except Exception as e:
        flash(f'Error fetching patient details: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))
    finally:
        cursor.close()

    return render_template('Doctors/view_patient.html', patient=patient, health_info=health_info,
                           user_name=user_name, 
                           user_email=user_email, 
                           user_image=user_image)



#========================================================Update Patient Admin Route===========================================================
#========================================================Update Patient Admin Route===========================================================

@app.route('/update_patient/<int:patient_id>', methods=['GET', 'POST'])
def update_patient(patient_id):
    if not session.get('is_admin'):
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))
    
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_image = session.get('user_image') or 'default_image.jpg'  # Provide a default image if None

    conn = mysql.connection
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        height = request.form.get('height')
        weight = request.form.get('weight')
        image = request.files.get('image')

        # Handle image upload
        if image:
            image_filename = secure_filename(image.filename)
            image_path = os.path.join('static/profile_images', image_filename)
            image.save(image_path)
        else:
            image_filename = request.form.get('current_image')

        try:
            cursor.execute("""
                UPDATE users
                SET name = %s, email = %s, height = %s, weight = %s, image = %s
                WHERE id = %s AND is_patient = TRUE
            """, (name, email, height, weight, image_filename, patient_id))
            conn.commit()
            flash('Patient information updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating patient information: {str(e)}', 'danger')
        finally:
            cursor.close()

        return redirect(url_for('admin_dashboard'))

    # Fetch the current information for the patient
    try:
        cursor.execute("""
            SELECT id, name, email, height, weight, image
            FROM users
            WHERE id = %s AND is_patient = TRUE
        """, (patient_id,))
        patient = cursor.fetchone()

        if not patient:
            flash('Patient not found!', 'danger')
            return redirect(url_for('admin_dashboard'))
    except Exception as e:
        flash(f'Error fetching patient details: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))
    finally:
        cursor.close()

    return render_template('Doctors/update_patient.html', patient=patient,
                           user_name=user_name, 
                           user_email=user_email, 
                           user_image=user_image) 


#========================================================Delete Patient Admin Route===========================================================
#========================================================Delete Patient Admin Route===========================================================
@app.route('/delete_patient/<int:patient_id>', methods=['POST'])
def delete_patient(patient_id):
    if not session.get('is_admin'):
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))

    conn = mysql.connection
    cursor = conn.cursor()

    try:
        cursor.execute("""
            DELETE FROM users
            WHERE id = %s AND is_patient = TRUE
        """, (patient_id,))
        conn.commit()
        flash('Patient deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting patient: {str(e)}', 'danger')
    finally:
        cursor.close()

    return redirect(url_for('admin_dashboard'))


#========================================================Appointment Route===========================================================
#========================================================Appointment Route===========================================================
@app.route('/appointment', methods=['GET', 'POST'])
def appointment():
    if not session.get('user_id'):
        flash('Please login first', 'danger')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    # Fetch all specializations
    cur.execute("SELECT DISTINCT specialization FROM doctors")
    specializations = cur.fetchall()

    if request.method == 'POST':
        patient_name = request.form['name']
        patient_email = request.form['email']
        doctor_id = request.form['doctor']
        appointment_date = request.form['date']
        appointment_time = request.form['time']

        try:
            # Check if doctor exists
            cur.execute("SELECT id, name, specialization FROM doctors WHERE id = %s", (doctor_id,))
            doctor = cur.fetchone()

            if not doctor:
                flash('Selected doctor does not exist.', 'danger')
                return redirect(url_for('appointment'))

            doctor_name = doctor[1]  # Doctor's name
            doctor_specialization = doctor[2]  # Doctor's specialization

            # Check if patient exists, if not create a new patient
            cur.execute("SELECT id FROM users WHERE email = %s AND user_type = 'user'", (patient_email,))
            patient = cur.fetchone()

            if not patient:
                # Generate a random password and hash it
                password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                hashed_password = generate_password_hash(password)
                # Insert new patient into the users table
                cur.execute("INSERT INTO users (name, email, password, user_type) VALUES (%s, %s, %s, 'user')", 
                            (patient_name, patient_email, hashed_password))
                mysql.connection.commit()
                patient_id = cur.lastrowid
                # Send the password to the new user
                send_email(patient_email, patient_name, 'account_creation', password=password)
            else:
                patient_id = patient[0]

            # Insert the appointment into the appointments table
            cur.execute("INSERT INTO appointments (patient_id, patient_name, patient_email, doctor_id, doctor_name, doctor_specialization, appointment_date, appointment_time, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Pending')",
                        (patient_id, patient_name, patient_email, doctor_id, doctor_name, doctor_specialization, appointment_date, appointment_time))
            mysql.connection.commit()

            # Send appointment confirmation email to the patient
            appointment_details = f"Your appointment with {doctor_name} ({doctor_specialization}) is scheduled for {appointment_date} at {appointment_time}."
            send_email(patient_email, patient_name, 'appointment_notification', appointment_details=appointment_details)

            flash('Appointment booked successfully!', 'success')
            return redirect(url_for('appointment'))

        except IntegrityError as e:
            mysql.connection.rollback()
            flash(f'Error occurred: {e}', 'danger')
        except Exception as e:
            mysql.connection.rollback()
            logging.error(f'Error occurred: {e}')
            flash(f'Unexpected error occurred: {e}', 'danger')

    cur.close()
    return render_template('users/appointment.html', specializations=specializations,
                           user_name=session.get('user_name'),
                           user_email=session.get('user_email'),
                           user_height=session.get('user_height'),
                           user_weight=session.get('user_weight'),
                           user_image=session.get('user_image'))




@app.route('/get_doctors')
def get_doctors():
    specialization = request.args.get('specialization')
    if specialization:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, name FROM doctors WHERE specialization = %s", (specialization,))
        doctors = cur.fetchall()
        cur.close()
        return jsonify([{'id': doc[0], 'name': doc[1]} for doc in doctors])
    return jsonify([])

@app.route('/manage_appointments', methods=['GET', 'POST'])
def manage_appointments():
    if not session.get('is_admin') and not session.get('is_super_admin'):
        flash('Access denied!', 'danger')
        return redirect(url_for('index'))

    conn = mysql.connection
    cur = conn.cursor()

    if request.method == 'POST':
        appointment_id = request.form['appointment_id']
        action = request.form['action']
        new_date = request.form.get('new_date')
        new_time = request.form.get('new_time')

        # Fetch appointment details
        cur.execute("""
            SELECT p.email, p.name, d.name AS doctor_name, a.appointment_date, a.appointment_time
            FROM appointments a
            JOIN users p ON a.patient_id = p.id
            JOIN doctors d ON a.doctor_id = d.id
            WHERE a.id = %s
        """, (appointment_id,))
        appointment_info = cur.fetchone()

        # Ensure appointment_info is not None
        if not appointment_info:
            flash('Appointment not found.', 'danger')
            return redirect(url_for('manage_appointments'))

        # Extract values from the tuple
        patient_email = appointment_info[0]
        patient_name = appointment_info[1]
        doctor_name = appointment_info[2]
        old_date = appointment_info[3]
        old_time = appointment_info[4]

        if action == 'approve':
            cur.execute("UPDATE appointments SET status = 'Approved' WHERE id = %s", (appointment_id,))
            appointment_details = f"Your appointment with Dr. {doctor_name} on {old_date} at {old_time} has been approved."
        elif action == 'reject':
            cur.execute("UPDATE appointments SET status = 'Rejected' WHERE id = %s", (appointment_id,))
            appointment_details = f"Your appointment with Dr. {doctor_name} on {old_date} at {old_time} has been rejected."
        elif action == 'reschedule' and new_date and new_time:
            cur.execute("""
                UPDATE appointments
                SET appointment_date = %s, appointment_time = %s, schedule_change_request_date = NULL
                WHERE id = %s
            """, (new_date, new_time, appointment_id))
            appointment_details = f"Your appointment with Dr. {doctor_name} has been rescheduled to {new_date} at {new_time}."

        conn.commit()
        flash('Appointment status updated successfully!', 'success')

        # Send email notification
        send_email(patient_email, patient_name, message_type='appointment_notification', appointment_details=appointment_details)
        
        return redirect(url_for('manage_appointments'))

    # Fetch appointments
    cur.execute("""
        SELECT a.id, p.name AS patient_name, p.email AS patient_email, d.name AS doctor_name, d.specialization, a.appointment_date, a.appointment_time, a.status, a.schedule_change_request_date
        FROM appointments a
        JOIN users p ON a.patient_id = p.id
        JOIN doctors d ON a.doctor_id = d.id
    """)
    appointments = cur.fetchall()
    cur.close()

    return render_template('Doctors/manage_appointments.html', appointments=appointments)

#========================================================Appointment Admin Route===========================================================
#========================================================Appointemt Admin Route===========================================================
@app.route('/admin_patient_appointments/<int:patient_id>', methods=['GET', 'POST'])
def admin_patient_appointments(patient_id):
    if not session.get('is_admin'):
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))

    conn = mysql.connection
    cursor = conn.cursor()
    appointments = []
    doctor_name = None

    try:
        # Fetch patient details and corresponding doctor
        cursor.execute("""
            SELECT u.name AS doctor_name, a.doctor_id
            FROM appointments a
            JOIN users u ON a.doctor_id = u.id
            WHERE a.patient_id = %s
            LIMIT 1
        """, (patient_id,))
        doctor_details = cursor.fetchone()

        if doctor_details:
            doctor_name = doctor_details[0]  # Doctor's name
            doctor_id = doctor_details[1]  # Doctor's ID
        else:
            flash('No appointments found for this patient.', 'warning')
            return render_template('admin_patient_appointments.html', patient_id=patient_id, appointments=[], doctor_name=None)

        # Fetch appointments for the doctor and patient where doctor's name matches
        cursor.execute("""
            SELECT a.id, a.doctor_id, a.doctor_name, a.doctor_specialization, a.appointment_date, a.appointment_time, a.status, a.schedule_change_request_date
            FROM appointments a
            WHERE a.patient_id = %s
        """, (patient_id,))
        appointments = cursor.fetchall()

        if request.method == 'POST':
            appointment_id = request.form['appointment_id']
            action = request.form['action']
            new_date = request.form.get('new_date')
            new_time = request.form.get('new_time')

            if action == 'approve':
                cursor.execute("UPDATE appointments SET status = 'Approved' WHERE id = %s", (appointment_id,))
            elif action == 'reject':
                cursor.execute("UPDATE appointments SET status = 'Rejected' WHERE id = %s", (appointment_id,))
            elif action == 'reschedule' and new_date and new_time:
                cursor.execute("UPDATE appointments SET appointment_date = %s, appointment_time = %s, schedule_change_request_date = NULL WHERE id = %s", 
                            (new_date, new_time, appointment_id))
            conn.commit()
            flash('Appointment status updated successfully!', 'success')
            return redirect(url_for('admin_patient_appointments', patient_id=patient_id))

    except Exception as e:
        flash(f'Error managing appointments: {str(e)}', 'danger')
        conn.rollback()
    finally:
        cursor.close()

    return render_template('Doctors/admin_patient_appointments.html', patient_id=patient_id, appointments=appointments, doctor_name=doctor_name)




#========================================================Appointment Show by User Route===========================================================
#========================================================Appointmemt Show by User Route===========================================================
from datetime import timedelta

def format_timedelta(td):
    """Convert timedelta to a string in HH:MM AM/PM format."""
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    period = 'AM' if hours < 12 else 'PM'
    hours = hours % 12
    hours = 12 if hours == 0 else hours
    return f"{hours:02}:{minutes:02} {period}"

@app.route('/user_appointments')
def user_appointments():
    if not session.get('user_id'):
        flash('Please log in first!', 'danger')
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_image = session.get('user_image')
    
    conn = mysql.connection
    cursor = conn.cursor()

    # Fetch user appointments
    cursor.execute("""
        SELECT a.id, d.name AS doctor_name, a.patient_name, d.specialization, a.appointment_date, a.appointment_time, a.status, a.schedule_change_request_date
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.patient_id = %s
    """, (user_id,))
    appointments = cursor.fetchall()
    cursor.close()

    # Format appointment times if necessary
    for appointment in appointments:
        if isinstance(appointment[5], timedelta):
            appointment = list(appointment)  # Convert tuple to list for mutability
            appointment[5] = format_timedelta(appointment[5])
            appointment = tuple(appointment)  # Convert back to tuple

    return render_template('users/user_appointments.html', 
                           appointments=appointments, 
                           user_name=user_name, 
                           user_email=user_email, 
                           user_image=user_image)




#========================================================GET Doctor Route===========================================================
#========================================================GET doctor Route===========================================================


@app.route('/search_doctor', methods=['GET', 'POST'])
def search_doctor():
    try:
        user_name = session.get('user_name')
        user_email = session.get('user_email')
        user_image = session.get('user_image')

        conn = mysql.connection
        cur = mysql.connection.cursor()
        query = "SELECT * FROM doctors WHERE 1=1"
        
        search_keyword = request.args.get('keyword')
        department = request.args.get('department')
        specialization = request.args.get('specialization')
        
        params = []
        
        if search_keyword:
            query += " AND (name LIKE %s OR email LIKE %s OR phone LIKE %s OR specialization LIKE %s)"
            search_keyword = f"%{search_keyword}%"
            params.extend([search_keyword, search_keyword, search_keyword, search_keyword])

        if department and department != "Department":
            query += " AND department = %s"
            params.append(department)

        if specialization and specialization != "All Specializations":
            query += " AND specialization = %s"
            params.append(specialization)

        cur.execute(query, params)
        doctors = cur.fetchall()
        cur.close()

        # Fetch list of specializations for filter dropdown
        cur = mysql.connection.cursor()
        cur.execute("SELECT DISTINCT specialization FROM doctors")
        specializations = cur.fetchall()
        cur.close()

        return render_template('Service/search_doctor.html', doctors=doctors, specializations=specializations, 
                               selected_specialization=specialization, user_name=user_name, 
                           user_email=user_email, 
                           user_image=user_image)
    except Exception as e:
        flash(f'Error fetching data from database: {str(e)}', 'danger')
        return render_template('Service/search_doctor.html', doctors=[], specializations=[], selected_specialization=None)
    




#=============================================Contact=============================================================================
#=============================================Contact=============================================================================


@app.route('/contact', methods=['POST'])
def contact():
    name = request.form['name']
    email = request.form['email']
    subject = request.form['subject']
    message = request.form['message']

    if not name or not email or not subject or not message:
        flash('All fields are required.', 'danger')
        return redirect(url_for('index'))

    contact_message = f"Name: {name}\nEmail: {email}\nSubject: {subject}\nMessage: {message}"

    conn = mysql.connection
    cursor = conn.cursor()

    try:
        # Insert the message into the contact_messages table
        cursor.execute("""
            INSERT INTO contact_messages (name, email, subject, message)
            VALUES (%s, %s, %s, %s)
        """, (name, email, subject, message))
        conn.commit()

        # Send the email
        send_email(email, message_type='contact_form', contact_message=contact_message)
        
        flash('Your message has been sent successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Failed to send your message. Please try again later. Error: {str(e)}', 'danger')
    finally:
        cursor.close()

    return redirect(url_for('index'))
#===============================================End Contact=======================================================
#===============================================End contact=========================================================

#===============================================Blog Start=======================================================
#===============================================Blog Start=========================================================

@app.route('/blog')
def blog():
    if 'user_id' not in session:
        flash('Please log in first!', 'danger')
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_image = session.get('user_image')

    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()

    return render_template("users/blog.html", 
                           user=user, 
                           user_name=user_name, 
                           user_email=user_email, 
                           user_image=user_image)


#========================================================ML Part===========================================================
#========================================================ML Part===========================================================

# load databasedataset===================================
sym_des = pd.read_csv("Dataset/symtoms_df.csv")
precautions = pd.read_csv("Dataset/precautions_df.csv")
workout = pd.read_csv("Dataset/workout_df.csv")
description = pd.read_csv("Dataset/description.csv")
medications = pd.read_csv('Dataset/medications.csv')
diets = pd.read_csv("Dataset/diets.csv")


# load model===========================================
svc = pickle.load(open('Model/svc.pkl','rb'))
 

#============================================================
# custome and helping functions
#==========================helper funtions================

# Helper function
def helper(dis):
    desc = description[description['Disease'] == dis]['Description']
    desc = " ".join([w for w in desc])

    pre = precautions[precautions['Disease'] == dis][['Precaution_1', 'Precaution_2', 'Precaution_3', 'Precaution_4']]
    pre = [col for col in pre.values]

    med = medications[medications['Disease'] == dis]['Medication']
    med = [med for med in med.values]

    die = diets[diets['Disease'] == dis]['Diet']
    die = [die for die in die.values]

    wrkout = workout[workout['disease'] == dis]['workout']

    return desc, pre, med, die, wrkout

symptoms_dict = {'itching': 0, 'skin_rash': 1, 'nodal_skin_eruptions': 2, 'continuous_sneezing': 3, 'shivering': 4, 'chills': 5, 'joint_pain': 6, 'stomach_pain': 7, 'acidity': 8, 'ulcers_on_tongue': 9, 'muscle_wasting': 10, 'vomiting': 11, 'burning_micturition': 12, 'spotting_ urination': 13, 'fatigue': 14, 'weight_gain': 15, 'anxiety': 16, 'cold_hands_and_feets': 17, 'mood_swings': 18, 'weight_loss': 19, 'restlessness': 20, 'lethargy': 
                 21, 'patches_in_throat': 
                 22, 'irregular_sugar_level': 23, 'cough': 24, 'high_fever': 25, 'sunken_eyes': 26, 'breathlessness': 27, 'sweating': 
                 28, 'dehydration': 29, 'indigestion': 30, 'headache': 31,
                   'yellowish_skin': 32, 'dark_urine': 33, 'nausea': 34, 'loss_of_appetite': 35,
                     'pain_behind_the_eyes': 36, 'back_pain': 37, 'constipation': 38, 'abdominal_pain': 39, 
                     'diarrhoea': 40, 'mild_fever': 41, 'yellow_urine': 42, 'yellowing_of_eyes': 43, 'acute_liver_failure': 
                     44, 'fluid_overload': 45, 'swelling_of_stomach': 46, 'swelled_lymph_nodes': 47, 'malaise': 48, 
                     'blurred_and_distorted_vision': 49, 'phlegm': 50, 'throat_irritation': 51, 'redness_of_eyes': 
                     52, 'sinus_pressure': 53, 'runny_nose': 54, 'congestion': 55, 'chest_pain': 56, 'weakness_in_limbs': 57, 'fast_heart_rate':
                       58, 'pain_during_bowel_movements': 59, 'pain_in_anal_region': 60, 'bloody_stool': 61, 'irritation_in_anus': 62, 'neck_pain': 63, 'dizziness': 64, 'cramps': 65, 'bruising': 66, 'obesity': 67, 'swollen_legs': 68, 'swollen_blood_vessels': 69, 'puffy_face_and_eyes': 70, 'enlarged_thyroid': 71, 'brittle_nails': 72, 'swollen_extremeties': 73, 'excessive_hunger': 74, 'extra_marital_contacts': 75, 'drying_and_tingling_lips': 76, 'slurred_speech': 77, 'knee_pain': 78, 'hip_joint_pain': 79, 'muscle_weakness': 80, 'stiff_neck': 81, 'swelling_joints': 82, 'movement_stiffness': 83, 'spinning_movements':
                         84, 'loss_of_balance': 85, 'unsteadiness': 86, 'weakness_of_one_body_side': 87, 'loss_of_smell': 88, 'bladder_discomfort': 89, 'foul_smell_of urine': 90, 'continuous_feel_of_urine': 91, 'passage_of_gases': 92, 'internal_itching': 93, 'toxic_look_(typhos)': 94, 'depression': 95, 'irritability': 96, 'muscle_pain': 97, 'altered_sensorium': 98, 'red_spots_over_body': 99, 'belly_pain': 100, 'abnormal_menstruation': 101, 'dischromic _patches': 102, 'watering_from_eyes': 103, 'increased_appetite': 104, 'polyuria': 105, 'family_history': 106, 'mucoid_sputum': 107, 'rusty_sputum': 108, 'lack_of_concentration': 109, 'visual_disturbances': 110, 'receiving_blood_transfusion': 111, 'receiving_unsterile_injections': 112, 'coma': 113, 
                     'stomach_bleeding': 114, 'distention_of_abdomen': 115, 'history_of_alcohol_consumption': 116, 'fluid_overload.1': 117, 'blood_in_sputum': 118, 'prominent_veins_on_calf': 119, 'palpitations': 120, 'painful_walking': 121, 'pus_filled_pimples': 122, 'blackheads': 123, 'scurring': 124, 'skin_peeling': 125, 'silver_like_dusting': 126, 'small_dents_in_nails': 127, 'inflammatory_nails': 128, 'blister': 129, 'red_sore_around_nose': 130, 'yellow_crust_ooze': 131}
diseases_list = {15: 'Fungal infection', 4: 'Allergy', 16: 'GERD', 9: 'Chronic cholestasis',
                  14: 'Drug Reaction', 33: 'Peptic ulcer diseae', 1: 'AIDS', 12: 'Diabetes ', 17: 'Gastroenteritis', 6: 'Bronchial Asthma', 23: 'Hypertension ', 30: 'Migraine', 7: 'Cervical spondylosis', 32: 'Paralysis (brain hemorrhage)', 28: 'Jaundice', 29: 'Malaria', 8: 'Chicken pox', 11: 'Dengue', 37: 'Typhoid', 40: 'hepatitis A', 19: 'Hepatitis B', 20: 'Hepatitis C', 21: 'Hepatitis D', 22: 'Hepatitis E', 3: 'Alcoholic hepatitis', 36: 'Tuberculosis', 10: 'Common Cold', 34: 'Pneumonia', 13: 'Dimorphic hemmorhoids(piles)', 18: 'Heart attack', 39: 'Varicose veins', 26: 'Hypothyroidism', 24: 'Hyperthyroidism', 25: 'Hypoglycemia', 31: 'Osteoarthristis', 5: 'Arthritis', 0: '(vertigo) Paroymsal  Positional Vertigo', 2: 'Acne', 38: 'Urinary tract infection', 35: 'Psoriasis', 27: 'Impetigo'}

# Model Prediction function
def get_predicted_value(patient_symptoms):
    input_vector = np.zeros(len(symptoms_dict))
    for item in patient_symptoms:
        input_vector[symptoms_dict[item]] = 1
    return diseases_list[svc.predict([input_vector])[0]]

@app.route('/predict', methods=['GET', 'POST'])
def home():
    if not session.get('user_id'):
        flash('Please login first', 'danger')
        return redirect(url_for('login'))
    
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_height = session.get('user_height')
    user_weight = session.get('user_weight')
    user_image = session.get('user_image')

    symptoms = list(symptoms_dict.keys())

    if request.method == 'POST':
        selected_symptoms = [
            request.form.get('symptom1'),
            request.form.get('symptom2'),
            request.form.get('symptom3'),
            request.form.get('symptom4')
        ]
        
        try:
            predicted_disease = get_predicted_value(selected_symptoms)
            dis_des, precautions, medications, rec_diet, workout = helper(predicted_disease)

            my_precautions = [precaution for precaution in precautions[0]]

            return render_template('Service/healthcheckresualt.html', predicted_disease=predicted_disease,
                                   dis_des=dis_des, my_precautions=my_precautions, medications=medications,
                                   my_diet=rec_diet, workout=workout, user_name=user_name,
                                   user_email=user_email, user_height=user_height, user_weight=user_weight,
                                   user_image=user_image)
        except KeyError as e:
            message = f"Symptom not recognized: {str(e)}. Please check your input."
            return render_template('Service/healthcheck.html', symptoms=symptoms, message=message)

    return render_template('Service/healthcheck.html', symptoms=symptoms, user_name=user_name,
                           user_email=user_email, user_height=user_height, user_weight=user_weight,
                           user_image=user_image)

@app.route('/healthcheck')
def healthcheck():
    if not session.get('user_id'):
        flash('Please login first', 'danger')
        return redirect(url_for('login'))
    
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_height = session.get('user_height')
    user_weight = session.get('user_weight')
    user_image = session.get('user_image')

    return render_template('Service/healthcheck.html', user_name=user_name, user_email=user_email, 
                           user_height=user_height, user_weight=user_weight, user_image=user_image)
    

#================================================ madicin part =========================================================
#================================================ madicin part =========================================================

# Load your data
df = pd.read_csv('Dataset/drugsComTest_raw.csv')

# Prepare data for recommendation
df = df[['drugName', 'condition']]
df.dropna(subset=['condition'], inplace=True)
tfidf_vectorizer = TfidfVectorizer()
tfidf_matrix = tfidf_vectorizer.fit_transform(df['condition'])

# Get known conditions
known_conditions = df['condition'].unique()

# Custom filter to zip two lists
@app.template_filter('zip_lists')
def zip_lists(a, b):
    return zip(a, b)


@app.route('/medicine')
def medicine():
    if not session.get('user_id'):
        flash('Please login first', 'danger')
        return redirect(url_for('login'))

    # Fetch user details from the session
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_image = session.get('user_image')

    # You can pass these details to the template if needed
    return render_template('/Service/Medicine.html', known_conditions=known_conditions, 
                           user_name=user_name, user_email=user_email, 
                           user_image=user_image)



@app.route('/recommend', methods=['POST'])
def recommend():
    if not session.get('user_id'):
        flash('Please login first', 'danger')
        return redirect(url_for('login'))
    
    # Fetch user details from the session
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_image = session.get('user_image')

    user_condition = request.form.get('condition').strip()

    # Initialize similarity_scores
    similarity_scores = None

    # Check if the user's condition is known
    if user_condition.lower() in map(str.lower, known_conditions):
        # If known, get recommendations directly
        top_medicines = df[df['condition'].str.lower() == user_condition.lower()]['drugName'].unique()
        if top_medicines.size == 0:
            return render_template('Service/medicineresult.html', error="No relevant medicines found for the given condition.", 
                                   condition=user_condition,
                                   user_name=user_name, user_email=user_email, 
                           user_image=user_image,)
        
        # Create Google search links
        medicine_links = [
            f"https://www.google.com/search?q={medicine.replace(' ', '+')}+site:drugs.com"
            for medicine in top_medicines
        ]
    else:
        # If not known, use similarity scoring
        user_condition_tfidf = tfidf_vectorizer.transform([user_condition])
        similarity_scores = cosine_similarity(user_condition_tfidf, tfidf_matrix)

        # Check if the highest similarity score is above a threshold
        threshold = 0.1
        if similarity_scores.max() < threshold:
            return render_template('/Service/medicineresult.html', error="No relevant medicines found for the given condition.", 
                                   condition=user_condition,user_name=user_name,
                                     user_email=user_email, 
                           user_image=user_image,)

        # Get top recommendations
        top_indices = similarity_scores.argsort()[0][::-1][:10]
        top_medicines = df['drugName'].iloc[top_indices]

        # Create Google search links
        medicine_links = [
            f"https://www.google.com/search?q={medicine.replace(' ', '+')}+site:drugs.com"
            for medicine in top_medicines
        ]

    return render_template('Service/medicineresult.html', medicines=top_medicines, links=medicine_links, condition=user_condition,
                           user_name=user_name, user_email=user_email, 
                           user_image=user_image,)


#================================================ madicin part  End =========================================================
#================================================ madicin part End =========================================================


#================================================ Emotion part start =========================================================
#================================================ Emotion part start  =========================================================


@app.route('/emotions')
def emotions():
    if not session.get('user_id'):
        flash('Please login first', 'danger')
        return redirect(url_for('login'))

    # Fetch user details from the session
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_image = session.get('user_image')

    return render_template('Service/emotions.html',
    user_name=user_name, 
                           user_email=user_email, 
                           user_image=user_image)


@app.route('/analyze', methods=['POST'])
def analyze():
    if not session.get('user_id'):
        flash('Please login first', 'danger')
        return redirect(url_for('login'))

    # Fetch user details from the session
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_image = session.get('user_image')


    text = request.form['mood']
    sentiment_score_vader = analyze_sentiment_vader(text)
    sentiment_score_bert = analyze_sentiment_bert(text)
    recommendations = recommend_coping_mechanisms(sentiment_score_vader)
    return render_template('Service/emotionsresult.html', 
                           score_vader=sentiment_score_vader, 
                           score_bert=sentiment_score_bert.numpy(), 
                           recommendations=recommendations,
                           user_name=user_name, user_email=user_email, 
                           user_image=user_image)



#================================================ Emotion part End =========================================================
#================================================ Emotion part End  =========================================================


#================================================ multiplediseases part Start =========================================================
#================================================ multiplediseases part Start  =========================================================

@app.route('/multiplediseases')
def multiplediseases():
    if not session.get('user_id'):
        flash('Please login first', 'danger')
        return redirect(url_for('login'))

    # Fetch user details from the session
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_image = session.get('user_image')

    # You can pass these details to the template if needed
    return render_template('/Service/MultipleDiseases/multiplediseases.html', known_conditions=known_conditions, 
                           user_name=user_name, user_email=user_email, 
                           user_image=user_image)



#================================================ diabetes part Start =========================================================
#================================================ diabetes part Start  =========================================================

# Load the trained model 
model = joblib.load(open('Model/diabetes.pkl', 'rb')) 
 
@app.route("/diabetes") 
def diabetes():
    if not session.get('user_id'):
        flash('Please login first', 'danger')
        return redirect(url_for('login'))

    # Fetch user details from the session
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_image = session.get('user_image')

    return render_template("Service/MultipleDiseases/diabetes.html", 
                           user_name=user_name, user_email=user_email, 
                           user_image=user_image) 
 
@app.route('/predictdiabetes', methods=['POST']) 
def predictdiabetes():
    if not session.get('user_id'):
        flash('Please login first', 'danger')
        return redirect(url_for('login'))

    # Fetch user details from the session
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_image = session.get('user_image')

    if request.method == 'POST': 
        # Extract user input from the form 
        preg = int(request.form['pregnancies']) 
        glucose = int(request.form['glucose']) 
        bp = int(request.form['bloodpressure']) 
        st = int(request.form['skinthickness']) 
        insulin = int(request.form['insulin']) 
        bmi = float(request.form['bmi']) 
        dpf = float(request.form['dpf'])  # Ensure this name matches the model's expected name 
        age = int(request.form['age']) 
 
        # Create a DataFrame with the user input 
        user_data = pd.DataFrame({ 
            'Pregnancies': [preg], 
            'Glucose': [glucose], 
            'BloodPressure': [bp], 
            'SkinThickness': [st], 
            'Insulin': [insulin], 
            'BMI': [bmi], 
            'DiabetesPedigreeFunction': [dpf],  # Match the feature name used during training 
            'Age': [age] 
        }) 
         
        # Perform diabetes prediction using your trained model 
        output = model.predict(user_data)[0]  # Ensure output is a scalar value 
 
        # Generate a Pandas report 
        prediction_report = generate_pandas_report(user_data, output) 
 
        # Pass the prediction, report, and user data to the template 
        return render_template('Service/MultipleDiseases/diab_result.html', prediction=output, 
                               prediction_report=prediction_report, user_data=user_data, 
                           user_name=user_name, user_email=user_email, 
                           user_image=user_image) 
 
def generate_pandas_report(user_data, prediction): 
    # Generate a simple HTML report for the user data and prediction 
    report_html = f""" 
    <p><strong>User Data:</strong></p> 
    {user_data.to_html()} 
    <p><strong>Prediction:</strong> {'High Risk of Diabetes' if prediction == 1 else 'Low Risk of Diabetes'}</p> 
    """ 
    return report_html 



#================================================ diabetes part End =========================================================
#================================================ diabetes part End  =========================================================

#================================================ breastcancer part Start =========================================================
#================================================ breastcancer part Start  =========================================================

# Load the model using joblib and pickle 
model_cancer = pickle.load(open('Model/cAancer.pkl', 'rb')) 
 
# HTML File routes 
 
@app.route("/breastcancer") 
def breastcancer(): 
    if not session.get('user_id'):
        flash('Please login first', 'danger')
        return redirect(url_for('login'))

    # Fetch user details from the session
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_image = session.get('user_image')

    return render_template("/Service/MultipleDiseases/breastcancer.html", 
                           user_name=user_name, user_email=user_email, 
                           user_image=user_image)
 
 
# Cancer prediction route 
@app.route('/predictcancer', methods=['POST'])
def predictcancer():
    if not session.get('user_id'):
        flash('Please login first', 'danger')
        return redirect(url_for('login'))
    
    # Fetch user details from the session
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_image = session.get('user_image')

    if request.method == 'POST':
        # Extract user input from the form
        clump_thickness = int(request.form['clump_thickness'])
        uniform_cell_size = int(request.form['uniform_cell_size'])
        uniform_cell_shape = int(request.form['uniform_cell_shape'])
        marginal_adhesion = int(request.form['marginal_adhesion'])
        single_epithelial_size = int(request.form['single_epithelial_size'])
        bare_nuclei = int(request.form['bare_nuclei'])
        bland_chromatin = int(request.form['bland_chromatin'])
        normal_nucleoli = int(request.form['normal_nucleoli'])
        mitoses = int(request.form['mitoses'])
    
        # Create a DataFrame with the user input
        user_data = pd.DataFrame({
            'Clump Thickness': [clump_thickness],
            'Uniform Cell size': [uniform_cell_size],
            'Uniform Cell shape': [uniform_cell_shape],
            'Marginal Adhesion': [marginal_adhesion],
            'Single Epithelial Cell Size': [single_epithelial_size],
            'Bare Nuclei': [bare_nuclei],
            'Bland Chromatin': [bland_chromatin],
            'Normal Nucleoli': [normal_nucleoli],
            'Mitoses': [mitoses],
        })
        
        # Perform cancer prediction using the trained model
        prediction = model_cancer.predict(user_data)[0]
    
        # Generate a Pandas report if risk is high
        if prediction == 4:
            prediction_report = generate_pandas_report(user_data, prediction)
            show_report = True
        else:
            prediction_report = None
            show_report = False
    
        # Pass the prediction, report, and user data to the template
        return render_template(
            '/Service/MultipleDiseases/breastcancer_result.html',
            prediction=prediction,
            prediction_report=prediction_report,
            user_data=user_data,
            user_name=user_name,
            user_email=user_email,
            user_image=user_image,
            show_report=show_report
        )


 

def generate_pandas_report(user_data, prediction): 
    # Generate a simple report based on the user data and prediction 
    report_html = f"<p>User Data: {user_data.to_html()}</p><p>Prediction: {'Malignant' if prediction == 1 else 'Benign'}</p>" 
    return report_html  
#================================================ breastcancer part End ============================================================
#================================================ breastcancer part End ============================================================

#================================================ Heart Disease part Start ===========================================================
#================================================ Heart Disease part Start  ===========================================================

# Heart Prediction Route
@app.route("/heartdisease")
def heartdisease():
    if not session.get('user_id'):
        flash('Please login first', 'danger')
        return redirect(url_for('login'))

    # Fetch user details from the session
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_image = session.get('user_image')

    return render_template("/Service/MultipleDiseases/heartdisease.html",
                           user_name=user_name,
                           user_email=user_email,
                           user_image=user_image)

# Prediction function
def PredictorHD(to_predict_list, size):
    to_predict = np.array(to_predict_list).reshape(1, size)
    if size == 13:
        loaded_model = joblib.load("Model/heart_model.pkl")  # Add your model filename here
        result = loaded_model.predict(to_predict)
    return result[0]

# Predict Heart Disease Route
@app.route('/predictHD', methods=["POST"])
def predictHD():
    if not session.get('user_id'):
        flash('Please login first', 'danger')
        return redirect(url_for('login'))

    # Fetch user details from the session
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_image = session.get('user_image')

    if request.method == "POST":
        to_predict_dict = request.form.to_dict()
        to_predict_list = list(to_predict_dict.values())
        to_predict_list = list(map(float, to_predict_list))
        if len(to_predict_list) == 13:
            result = PredictorHD(to_predict_list, 13)

        if int(result) == 1:
            prediction = "Sorry! It seems you may have the disease. Please consult a doctor immediately."
            color = "text-danger"  # Red color for dangerous symptoms
        else:
            prediction = "No need to fear. You have no dangerous symptoms of the disease."
            color = "text-success"  # Green color for safe results

        # Pass the parameters to the template
        return render_template(
            "/Service/MultipleDiseases/heartdiseaseresult.html",
            user_name=user_name,
            user_email=user_email,
            user_image=user_image,
            prediction_text=prediction,
            prediction_color=color,
            age=to_predict_dict['age'],
            sex=to_predict_dict['sex'],
            cp=to_predict_dict['cp'],
            trestbps=to_predict_dict['trestbps'],
            chol=to_predict_dict['chol'],
            fbs=to_predict_dict['fbs'],
            restecg=to_predict_dict['restecg'],
            thalach=to_predict_dict['thalach'],
            exang=to_predict_dict['exang'],
            oldpeak=to_predict_dict['oldpeak'],
            slope=to_predict_dict['slope'],
            ca=to_predict_dict['ca'],
            thal=to_predict_dict['thal']
        )

#================================================ Heart Disease part End ===========================================================
#================================================ Heart Disease part End  ===========================================================

#================================================ Kidney Disease part start ===========================================================
#================================================Kidney Disease part start ===========================================================

# Load the trained model
rf_model = joblib.load('Model/Kidney.pkl')

@app.route('/kidney')
def kidney():
    if not session.get('user_id'):
        flash('Please login first', 'danger')
        return redirect(url_for('login'))

    # Fetch user details from the session
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_image = session.get('user_image')

    return render_template('/Service/MultipleDiseases/kidney.html',
                         user_name=user_name,
                           user_email=user_email,
                           user_image=user_image) 


@app.route('/predictkidney', methods=['POST'])
def predictkidney():
    if not session.get('user_id'):
        flash('Please login first', 'danger')
        return redirect(url_for('login'))

    # Fetch user details from the session
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_image = session.get('user_image')

    if request.method == 'POST':
        # Retrieve form data
        features = {feature: float(request.form.get(feature)) for feature in [
            'sg', 'htn', 'hemo', 'dm', 'al', 'appet', 'rc', 'pc'
        ]}
        features_list = [features[feature] for feature in [
            'sg', 'htn', 'hemo', 'dm', 'al', 'appet', 'rc', 'pc'
        ]]

        # Convert features to numpy array
        features_array = np.array([features_list])

        # Predict using the preloaded Random Forest model
        prediction = rf_model.predict(features_array)

        # Convert prediction to human-readable label
        result = 'Sorry! It seems you may have the disease. Please consult a doctor immediately.' if prediction == 1 else 'No need to fear.You have no dangerous symptoms of the disease.'

        return render_template('/Service/MultipleDiseases/kidneyresult.html', prediction=result, **features,user_name=user_name,
                           user_email=user_email,
                           user_image=user_image)

#================================================ Kidney Disease part End ===========================================================
#================================================ Kidneys  Disease part End ===========================================================


if __name__ == '__main__':
    app.run(debug=True)