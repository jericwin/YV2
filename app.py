from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
import bcrypt
import random
import string
import os
import smtplib
from werkzeug.utils import secure_filename
from email.mime.text import MIMEText
from dotenv import load_dotenv
import threading
import google.generativeai as genai

load_dotenv()

def send_async_email(sender_email, sender_password, recipient_email, msg_content, subject):
    try:
        msg = MIMEText(msg_content)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient_email

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print(f"Sent email to {recipient_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")

app = Flask(__name__)
# Enable CORS for all routes so the HTML file can communicate with the backend
CORS(app)

# Database Configuration for XAMPP
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',       # default XAMPP username
    'password': '',       # default XAMPP password is empty
    'database': 'yv2_db'
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    fname = data.get('fname')
    mname = data.get('mname')
    lname = data.get('lname')
    extension = data.get('extension')
    email = data.get('email')
    password = data.get('password')
    role = 'buyer' # Force role to buyer as requested

    # Address fields
    region = data.get('region')
    province = data.get('province')
    city = data.get('city')
    barangay = data.get('barangay')
    zipcode = data.get('zipcode')
    street = data.get('street')
    house_number = data.get('house_number')

    if not all([fname, lname, email, password]):
        return jsonify({'error': 'All fields are required.'}), 400

    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Generate 6-digit verification code
    verification_code = ''.join(random.choices(string.digits, k=6))
    
    # Send actual email via SMTP
    sender_email = os.environ.get('SMTP_EMAIL')
    sender_password = os.environ.get('SMTP_PASSWORD')
    
    if sender_email and sender_password:
        msg_content = f"Your verification code is: {verification_code}"
        subject = 'Verify your YouVersion2 Account'
        thread = threading.Thread(target=send_async_email, args=(sender_email, sender_password, email, msg_content, subject))
        thread.start()
        print(f"Started thread to send email verification code {verification_code} to {email}")
    else:
        print(f"--- MOCK EMAIL: Sending verification code {verification_code} to {email} ---")

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed.'}), 500

    cursor = conn.cursor()
    try:
        query = """INSERT INTO users 
                   (fname, mname, lname, extension, email, password, role, region, province, city, barangay, zipcode, street, house_number, is_verified, verification_code) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        values = (fname, mname, lname, extension, email, hashed_password.decode('utf-8'), role, region, province, city, barangay, zipcode, street, house_number, 0, verification_code)
        cursor.execute(query, values)
        conn.commit()
        return jsonify({'message': 'User registered successfully! Please verify your email.', 'email': email}), 201
    except mysql.connector.IntegrityError:
        return jsonify({'error': 'Email already exists.'}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/verify-email', methods=['POST'])
def verify_email():
    data = request.json
    email = data.get('email')
    code = data.get('code')

    if not email or not code:
        return jsonify({'error': 'Email and verification code are required.'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed.'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        query = "SELECT verification_code FROM users WHERE email = %s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()

        if user and user['verification_code'] == code:
            update_query = "UPDATE users SET is_verified = 1 WHERE email = %s"
            cursor.execute(update_query, (email,))
            conn.commit()
            return jsonify({'message': 'Email verified successfully!'}), 200
        else:
            return jsonify({'error': 'Invalid verification code.'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    email = data.get('email')

    if not email:
        return jsonify({'error': 'Email is required.'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed.'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user:
            # For security, you might want to return success even if not found, but we return error here for simplicity
            return jsonify({'error': 'No account found with that email.'}), 404

        verification_code = ''.join(random.choices(string.digits, k=6))
        
        sender_email = os.environ.get('SMTP_EMAIL')
        sender_password = os.environ.get('SMTP_PASSWORD')
        
        if sender_email and sender_password:
            msg_content = f"Your password reset code is: {verification_code}"
            subject = 'Reset your YouVersion2 Password'
            thread = threading.Thread(target=send_async_email, args=(sender_email, sender_password, email, msg_content, subject))
            thread.start()
            print(f"Started thread to send password reset code {verification_code} to {email}")
        else:
            print(f"--- MOCK EMAIL: Sending password reset code {verification_code} to {email} ---")

        update_query = "UPDATE users SET verification_code = %s WHERE email = %s"
        cursor.execute(update_query, (verification_code, email))
        conn.commit()

        return jsonify({'message': 'Password reset code sent to your email.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/verify-forgot-password-otp', methods=['POST'])
def verify_forgot_password_otp():
    data = request.json
    email = data.get('email')
    code = data.get('code')

    if not email or not code:
        return jsonify({'error': 'Email and verification code are required.'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed.'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        query = "SELECT verification_code FROM users WHERE email = %s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()

        if user and user['verification_code'] == code:
            return jsonify({'message': 'OTP verified successfully!'}), 200
        else:
            return jsonify({'error': 'Invalid verification code.'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    email = data.get('email')
    code = data.get('code')
    new_password = data.get('password')

    if not email or not code or not new_password:
        return jsonify({'error': 'Email, code, and new password are required.'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed.'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        query = "SELECT verification_code FROM users WHERE email = %s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()

        if user and user['verification_code'] == code:
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            # Clear verification code and update password
            update_query = "UPDATE users SET password = %s, verification_code = NULL WHERE email = %s"
            cursor.execute(update_query, (hashed_password.decode('utf-8'), email))
            conn.commit()
            return jsonify({'message': 'Password reset successfully!'}), 200
        else:
            return jsonify({'error': 'Invalid or expired verification code.'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed.'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        query = "SELECT * FROM users WHERE email = %s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            if not user.get('is_verified', True):
                return jsonify({'error': 'Please verify your email before logging in.'}), 403
            
            # Don't send the password back to the client
            user_data = {
                'id': user['id'],
                'fname': user['fname'],
                'mname': user['mname'],
                'lname': user['lname'],
                'extension': user['extension'],
                'email': user['email'],
                'role': user['role'],
                'profile_image': user['profile_image']
            }
            return jsonify({'message': 'Login successful!', 'user': user_data}), 200
        else:
            return jsonify({'error': 'Invalid email or password.'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/books', methods=['POST'])
def add_book():
    data = request.json
    seller_id = data.get('seller_id')
    title = data.get('title')
    description = data.get('description')
    author = data.get('author')
    genre = data.get('genre')
    price = data.get('price')
    stock = data.get('stock', 0)
    cover_image = data.get('cover_image', '')

    if not all([seller_id, title, author, price]):
        return jsonify({'error': 'Missing required fields.'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed.'}), 500

    cursor = conn.cursor()
    try:
        query = """INSERT INTO books (seller_id, title, description, author, genre, price, stock, cover_image) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        values = (seller_id, title, description, author, genre, price, stock, cover_image)
        cursor.execute(query, values)
        conn.commit()
        return jsonify({'message': 'Book added successfully!'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/books', methods=['GET'])
def get_books():
    seller_id = request.args.get('seller_id')
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed.'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        if seller_id:
            query = "SELECT * FROM books WHERE seller_id = %s ORDER BY created_at DESC"
            cursor.execute(query, (seller_id,))
        else:
            query = "SELECT * FROM books ORDER BY created_at DESC"
            cursor.execute(query)
        books = cursor.fetchall()
        return jsonify(books), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user_profile(user_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed.'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        # Fetch user
        cursor.execute("SELECT id, fname, mname, lname, extension, email, role, profile_image FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'error': 'User not found.'}), 404
            
        # Fetch addresses
        cursor.execute("SELECT * FROM user_addresses WHERE user_id = %s ORDER BY is_default DESC", (user_id,))
        addresses = cursor.fetchall()
        user['addresses'] = addresses
        
        return jsonify(user), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/user/<int:user_id>/avatar', methods=['POST'])
def upload_avatar(user_id):
    if 'avatar' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        filename = secure_filename(file.filename)
        filename = f"user_{user_id}_{filename}"
        upload_folder = os.path.join('.', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        url_path = f"/uploads/{filename}"
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed.'}), 500
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET profile_image = %s WHERE id = %s", (url_path, user_id))
            conn.commit()
            return jsonify({'message': 'Profile image updated successfully!', 'profile_image': url_path}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()

@app.route('/api/user/<int:user_id>/address', methods=['POST'])
def add_user_address(user_id):
    data = request.json
    street = data.get('street')
    barangay = data.get('barangay')
    city = data.get('city')
    province = data.get('province')
    zipcode = data.get('zipcode')
    country = data.get('country', 'PH')
    is_default = data.get('is_default', 0)
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed.'}), 500
    cursor = conn.cursor()
    try:
        # If this is set as default, remove default from others
        if int(is_default) == 1:
            cursor.execute("UPDATE user_addresses SET is_default = 0 WHERE user_id = %s", (user_id,))
            
        # If it's the first address, make it default automatically
        cursor.execute("SELECT COUNT(*) FROM user_addresses WHERE user_id = %s", (user_id,))
        count = cursor.fetchone()[0]
        if count == 0:
            is_default = 1
            
        query = """INSERT INTO user_addresses (user_id, street, barangay, city, province, zipcode, country, is_default)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (user_id, street, barangay, city, province, zipcode, country, is_default))
        conn.commit()
        return jsonify({'message': 'Address added successfully!'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/user/<int:user_id>/address/<int:address_id>', methods=['DELETE'])
def delete_user_address(user_id, address_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed.'}), 500
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM user_addresses WHERE user_id = %s AND id = %s", (user_id, address_id))
        conn.commit()
        return jsonify({'message': 'Address deleted successfully!'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/user/<int:user_id>/address/<int:address_id>/default', methods=['PUT'])
def set_default_address(user_id, address_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed.'}), 500
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE user_addresses SET is_default = 0 WHERE user_id = %s", (user_id,))
        cursor.execute("UPDATE user_addresses SET is_default = 1 WHERE user_id = %s AND id = %s", (user_id, address_id))
        conn.commit()
        return jsonify({'message': 'Default address updated successfully!'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/user/<int:user_id>/send_otp', methods=['POST'])
def send_otp(user_id):
    data = request.json
    # Can optionally provide an email to send to, otherwise we use the user's current email
    target_email = data.get('email') 
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed.'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        if not target_email:
            cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            if not user:
                return jsonify({'error': 'User not found'}), 404
            target_email = user['email']
            
        verification_code = ''.join(random.choices(string.digits, k=6))
        
        # Send actual email via SMTP
        sender_email = os.environ.get('SMTP_EMAIL')
        sender_password = os.environ.get('SMTP_PASSWORD')
        
        if sender_email and sender_password:
            msg_content = f"Your verification code is: {verification_code}"
            subject = 'Security Verification - YouVersion2'
            thread = threading.Thread(target=send_async_email, args=(sender_email, sender_password, target_email, msg_content, subject))
            thread.start()
            print(f"Started thread to send security verification code {verification_code} to {target_email}")
        else:
            print(f"--- MOCK EMAIL: Sending security code {verification_code} to {target_email} ---")
            
        # Update user's verification code
        cursor.execute("UPDATE users SET verification_code = %s WHERE id = %s", (verification_code, user_id))
        conn.commit()
        return jsonify({'message': 'OTP sent successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/user/<int:user_id>/verify_otp', methods=['POST'])
def verify_otp(user_id):
    data = request.json
    code = data.get('code')
    
    if not code:
        return jsonify({'error': 'Code is required'}), 400
        
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed.'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT verification_code FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user or str(user['verification_code']) != str(code):
            return jsonify({'error': 'Invalid verification code'}), 400
            
        # Clear the code after successful verification
        cursor.execute("UPDATE users SET verification_code = NULL WHERE id = %s", (user_id,))
        conn.commit()
        return jsonify({'message': 'Verified successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/user/<int:user_id>/verify_password', methods=['POST'])
def verify_password(user_id):
    data = request.json
    password = data.get('password')
    if not password:
        return jsonify({'error': 'Password is required'}), 400
        
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed.'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT password FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        # bcrypt check
        stored_hash = user['password']
        if not bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
            return jsonify({'error': 'Incorrect current password'}), 401
            
        return jsonify({'message': 'Password verified successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/user/<int:user_id>/password', methods=['PUT'])
def update_password(user_id):
    data = request.json
    new_password = data.get('password')
    if not new_password:
        return jsonify({'error': 'Password is required'}), 400
        
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed.'}), 500
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_password.decode('utf-8'), user_id))
        conn.commit()
        return jsonify({'message': 'Password updated successfully!'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/user/<int:user_id>/email', methods=['PUT'])
def update_email(user_id):
    data = request.json
    new_email = data.get('email')
    if not new_email:
        return jsonify({'error': 'Email is required'}), 400
        
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed.'}), 500
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET email = %s WHERE id = %s", (new_email, user_id))
        conn.commit()
        return jsonify({'message': 'Email updated successfully!'}), 200
    except mysql.connector.IntegrityError:
        return jsonify({'error': 'Email already exists.'}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/seller/books/<int:book_id>/feature', methods=['POST'])
def feature_book(book_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Unfeature all books
        cursor.execute("UPDATE books SET is_featured = 0")
        
        # Feature the specific book
        cursor.execute("UPDATE books SET is_featured = 1 WHERE id = %s", (book_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Book featured successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/featured-book', methods=['GET'])
def get_featured_book():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM books WHERE is_featured = 1 LIMIT 1")
        book = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if book:
            return jsonify({'book': book})
        else:
            return jsonify({'book': None})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def send_static(path):
    return send_from_directory('.', path)

from flask import Response, stream_with_context
import json

# Cache FAQs globally to avoid disk I/O on every request
faqs_text = ""
try:
    with open('faqs.json', 'r') as f:
        faqs = json.load(f)
        faqs_text = "Here are the FAQs you can use to answer questions:\n"
        for item in faqs:
            faqs_text += f"Q: {item.get('question')}\nA: {item.get('answer')}\n\n"
except:
    pass
# Initialize Gemini once globally
api_key_global = os.environ.get('GEMINI_API_KEY')
chat_model = None
if api_key_global:
    genai.configure(api_key=api_key_global)
    chat_model = genai.GenerativeModel('gemini-flash-latest')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    if not message:
        return jsonify({'error': 'Message is required'}), 400
        
    if not chat_model:
        return jsonify({'error': 'Gemini API key is not configured.'}), 500
        
    try:
        def generate():
            # Force Werkzeug/Flask to flush headers and start stream immediately
            yield " " * 1024 
            
            try:
                prompt = f"You are a helpful bookstore AI assistant named 'YV2 AI'. Respond politely and concisely to the following user message.\n\n{faqs_text}\n\nUser: {message}"
                response = chat_model.generate_content(prompt, stream=True)
                for chunk in response:
                    yield chunk.text
            except Exception as e:
                yield f"\n[Error: {str(e)}]"
                
        resp = Response(stream_with_context(generate()), mimetype='text/plain')
        resp.headers['X-Accel-Buffering'] = 'no'
        resp.headers['Cache-Control'] = 'no-cache'
        return resp
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def send_chat():
    data = request.json
    buyer_id = data.get('buyer_id')
    seller_id = data.get('seller_id')
    sender = data.get('sender')
    message = data.get('message')

    if not all([buyer_id, seller_id, sender, message]):
        return jsonify({'error': 'Missing fields'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO chats (buyer_id, seller_id, sender, message) VALUES (%s, %s, %s, %s)",
            (buyer_id, seller_id, sender, message)
        )
        conn.commit()
        return jsonify({'success': True}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/chat/<int:buyer_id>/<int:seller_id>', methods=['GET'])
def get_chat_history(buyer_id, seller_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM chats WHERE buyer_id = %s AND seller_id = %s ORDER BY created_at ASC",
            (buyer_id, seller_id)
        )
        chats = cursor.fetchall()
        return jsonify(chats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/chat/conversations/<int:user_id>/<string:role>', methods=['GET'])
def get_conversations(user_id, role):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if role == 'seller':
            # Get distinct buyers who chatted with this seller
            cursor.execute('''
                SELECT DISTINCT u.id, u.fname, u.lname, u.profile_image 
                FROM chats c 
                JOIN users u ON c.buyer_id = u.id 
                WHERE c.seller_id = %s
            ''', (user_id,))
        else:
            # Get distinct sellers who this buyer chatted with
            cursor.execute('''
                SELECT DISTINCT u.id, u.fname, u.lname, u.profile_image 
                FROM chats c 
                JOIN users u ON c.seller_id = u.id 
                WHERE c.buyer_id = %s
            ''', (user_id,))
        conversations = cursor.fetchall()
        
        # Add the last message for each conversation
        for conv in conversations:
            if role == 'seller':
                cursor.execute('SELECT message, created_at FROM chats WHERE buyer_id = %s AND seller_id = %s ORDER BY created_at DESC LIMIT 1', (conv['id'], user_id))
            else:
                cursor.execute('SELECT message, created_at FROM chats WHERE buyer_id = %s AND seller_id = %s ORDER BY created_at DESC LIMIT 1', (user_id, conv['id']))
            last_msg = cursor.fetchone()
            if last_msg:
                conv['last_message'] = last_msg['message']
                conv['last_time'] = last_msg['created_at'].isoformat() if last_msg['created_at'] else None
        
        return jsonify(conversations), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    app.run(debug=True, port=5000)
