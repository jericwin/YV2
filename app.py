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

load_dotenv()

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
        try:
            msg = MIMEText(f"Your verification code is: {verification_code}")
            msg['Subject'] = 'Verify your YouVersion2 Account'
            msg['From'] = sender_email
            msg['To'] = email

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(sender_email, sender_password)
                server.send_message(msg)
            print(f"Sent real email verification code {verification_code} to {email}")
        except Exception as e:
            print(f"Failed to send email: {e}")
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

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def send_static(path):
    return send_from_directory('.', path)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
