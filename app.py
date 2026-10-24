from flask import Flask, request, jsonify, send_from_directory, session, abort, Response, stream_with_context
from flask_cors import CORS
import mysql.connector
import bcrypt
import random
import string
import os
import re
import json
import uuid
import base64
import secrets
import smtplib
import threading
from datetime import datetime, timedelta, date
from decimal import Decimal
from functools import wraps
from contextlib import contextmanager
from werkzeug.utils import secure_filename
from email.mime.text import MIMEText
from dotenv import load_dotenv

try:
    import google.generativeai as genai
except ImportError:  # the AI assistant is optional
    genai = None

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')

# ── Business rules (mirrors the storefront so the server is the source of truth) ──
PROMO_CODES = {'READ15': Decimal('0.15')}
FREE_SHIPPING_THRESHOLD = Decimal('35')
SHIPPING_FEE = Decimal('4.99')
MAX_QTY_PER_TITLE = 10
CODE_TTL_MINUTES = 15
OTP_GRACE_MINUTES = 10
ORDER_STATUSES = ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']
ACTIVE_STATUSES = ('Pending', 'Processing', 'Shipped')

# Seller team roles and what each one may do
TEAM_PERMISSIONS = {
    'admin': {'books', 'orders', 'reviews', 'messages', 'team', 'store'},
    'manager': {'books', 'orders', 'reviews', 'messages'},
    'fulfillment': {'orders'},
    'support': {'reviews', 'messages'},
}

ALLOWED_IMAGE_TYPES = {'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp', 'image/gif': 'gif'}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


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


def send_email(recipient, subject, body):
    """Send in the background when SMTP is configured, otherwise log a mock email."""
    sender_email = os.environ.get('SMTP_EMAIL')
    sender_password = os.environ.get('SMTP_PASSWORD')
    if sender_email and sender_password:
        threading.Thread(target=send_async_email,
                         args=(sender_email, sender_password, recipient, body, subject),
                         daemon=True).start()
        print(f"Started thread to send '{subject}' to {recipient}")
    else:
        print(f"--- MOCK EMAIL to {recipient} | {subject} ---\n{body}\n--- END MOCK EMAIL ---")


def _load_secret_key():
    key = os.environ.get('SECRET_KEY')
    if key:
        return key
    # Local fallback: persist a generated key so sessions survive restarts
    path = os.path.join(BASE_DIR, '.flask_secret')
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        key = secrets.token_hex(32)
        try:
            with open(path, 'w') as f:
                f.write(key)
        except OSError:
            pass
        return key


app = Flask(__name__)
app.secret_key = _load_secret_key()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=bool(os.environ.get('RENDER') or os.environ.get('SESSION_COOKIE_SECURE')),
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    MAX_CONTENT_LENGTH=12 * 1024 * 1024,
)
# Enable CORS for all routes so the HTML file can communicate with the backend
CORS(app)

# Database Configuration — reads from env vars for production, falls back to local XAMPP
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', '127.0.0.1'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'yv2_db'),
    'port': int(os.environ.get('DB_PORT', 3306)),
}


def get_db_connection():
    try:
        config = dict(DB_CONFIG)
        # Cloud MySQL (Aiven, TiDB Cloud, etc.) requires SSL in production
        host = os.environ.get('DB_HOST', '')
        if host.endswith('aiven.io') or host.endswith('tidbcloud.com') or os.environ.get('DB_SSL', '').lower() in ('1', 'true'):
            config['ssl_disabled'] = False
        connection = mysql.connector.connect(**config)
        return connection
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


@app.errorhandler(ApiError)
def handle_api_error(err):
    return jsonify({'error': err.message}), err.status


@app.errorhandler(413)
def handle_too_large(_err):
    return jsonify({'error': 'Upload is too large (max 5MB per image).'}), 413


@app.errorhandler(mysql.connector.Error)
def handle_db_error(err):
    print(f"Database error: {err}")
    return jsonify({'error': 'A database error occurred. Please try again.'}), 500


@contextmanager
def db(dictionary=True):
    """Yield (connection, cursor); commits on success, rolls back on error."""
    conn = get_db_connection()
    if not conn:
        raise ApiError('Database connection failed.', 503)
    cursor = conn.cursor(dictionary=dictionary)
    try:
        yield conn, cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Schema: created / upgraded automatically so a fresh database just works
# ─────────────────────────────────────────────────────────────────────────────
SCHEMA = [
    """CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        fname VARCHAR(100) NOT NULL,
        mname VARCHAR(100) DEFAULT NULL,
        lname VARCHAR(100) NOT NULL,
        extension VARCHAR(20) DEFAULT NULL,
        email VARCHAR(255) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL,
        role VARCHAR(50) NOT NULL DEFAULT 'buyer',
        region VARCHAR(100) DEFAULT NULL,
        province VARCHAR(100) DEFAULT NULL,
        city VARCHAR(100) DEFAULT NULL,
        barangay VARCHAR(100) DEFAULT NULL,
        zipcode VARCHAR(20) DEFAULT NULL,
        street VARCHAR(255) DEFAULT NULL,
        house_number VARCHAR(50) DEFAULT NULL,
        is_verified TINYINT(1) NOT NULL DEFAULT 0,
        verification_code VARCHAR(10) DEFAULT NULL,
        bio TEXT DEFAULT NULL,
        profile_image VARCHAR(255) DEFAULT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS books (
        id INT AUTO_INCREMENT PRIMARY KEY,
        seller_id INT NOT NULL,
        title VARCHAR(255) NOT NULL,
        description TEXT,
        author VARCHAR(100) NOT NULL,
        genre VARCHAR(100),
        price DECIMAL(10,2) NOT NULL,
        stock INT NOT NULL DEFAULT 0,
        cover_image LONGTEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        is_featured TINYINT(1) DEFAULT 0,
        FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS orders (
        id INT AUTO_INCREMENT PRIMARY KEY,
        buyer_id INT NULL,
        total_amount DECIMAL(10,2) NOT NULL,
        status VARCHAR(50) DEFAULT 'Pending',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (buyer_id) REFERENCES users(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS order_items (
        id INT AUTO_INCREMENT PRIMARY KEY,
        order_id INT NOT NULL,
        book_id INT NOT NULL,
        quantity INT NOT NULL,
        price DECIMAL(10,2) NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS user_addresses (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        street VARCHAR(255) DEFAULT NULL,
        barangay VARCHAR(100) DEFAULT NULL,
        city VARCHAR(100) DEFAULT NULL,
        province VARCHAR(100) DEFAULT NULL,
        zipcode VARCHAR(20) DEFAULT NULL,
        country VARCHAR(10) DEFAULT 'PH',
        is_default TINYINT(1) DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS chats (
        id INT AUTO_INCREMENT PRIMARY KEY,
        buyer_id INT NOT NULL,
        seller_id INT NOT NULL,
        sender VARCHAR(10) NOT NULL,
        message TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (buyer_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS reviews (
        id INT AUTO_INCREMENT PRIMARY KEY,
        book_id INT NOT NULL,
        buyer_id INT NOT NULL,
        rating TINYINT NOT NULL,
        comment TEXT,
        reply TEXT,
        replied_at DATETIME NULL,
        helpful_count INT NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY one_review_per_buyer (book_id, buyer_id),
        FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
        FOREIGN KEY (buyer_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS notifications (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        type VARCHAR(20) NOT NULL DEFAULT 'system',
        title VARCHAR(255) NOT NULL,
        body TEXT,
        link VARCHAR(255),
        is_read TINYINT(1) NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        KEY user_unread (user_id, is_read),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS store_settings (
        id INT PRIMARY KEY,
        store_name VARCHAR(255) NOT NULL,
        contact_email VARCHAR(255),
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS activity_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NULL,
        action VARCHAR(255) NOT NULL,
        ip_address VARCHAR(64),
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
]

# Columns added after the original schema: (table, column, definition)
COLUMN_UPGRADES = [
    # Columns older databases may be missing (they were added by hand-run migration scripts)
    ('users', 'mname', 'VARCHAR(100) DEFAULT NULL'),
    ('users', 'extension', 'VARCHAR(20) DEFAULT NULL'),
    ('users', 'region', 'VARCHAR(100) DEFAULT NULL'),
    ('users', 'province', 'VARCHAR(100) DEFAULT NULL'),
    ('users', 'city', 'VARCHAR(100) DEFAULT NULL'),
    ('users', 'barangay', 'VARCHAR(100) DEFAULT NULL'),
    ('users', 'zipcode', 'VARCHAR(20) DEFAULT NULL'),
    ('users', 'street', 'VARCHAR(255) DEFAULT NULL'),
    ('users', 'house_number', 'VARCHAR(50) DEFAULT NULL'),
    ('users', 'is_verified', 'TINYINT(1) NOT NULL DEFAULT 1'),  # existing accounts stay usable
    ('users', 'verification_code', 'VARCHAR(10) DEFAULT NULL'),
    ('users', 'bio', 'TEXT DEFAULT NULL'),
    ('users', 'profile_image', 'VARCHAR(255) DEFAULT NULL'),
    ('users', 'phone', 'VARCHAR(40) DEFAULT NULL'),
    ('users', 'display_name', 'VARCHAR(120) DEFAULT NULL'),
    ('users', 'code_expires_at', 'DATETIME NULL'),
    ('users', 'team_role', 'VARCHAR(20) DEFAULT NULL'),
    ('users', 'invite_status', "VARCHAR(20) DEFAULT 'active'"),
    ('books', 'is_featured', 'TINYINT(1) DEFAULT 0'),
    ('books', 'original_price', 'DECIMAL(10,2) NULL'),
    ('books', 'pages', 'INT NULL'),
    ('books', 'publisher', 'VARCHAR(255) NULL'),
    ('books', 'isbn', 'VARCHAR(40) NULL'),
    ('books', 'is_active', 'TINYINT(1) NOT NULL DEFAULT 1'),
    ('orders', 'reference', 'VARCHAR(20) NULL'),
    ('orders', 'ship_fname', 'VARCHAR(100) NULL'),
    ('orders', 'ship_lname', 'VARCHAR(100) NULL'),
    ('orders', 'ship_email', 'VARCHAR(255) NULL'),
    ('orders', 'ship_address', 'VARCHAR(255) NULL'),
    ('orders', 'ship_city', 'VARCHAR(100) NULL'),
    ('orders', 'ship_zip', 'VARCHAR(20) NULL'),
    ('orders', 'payment_method', "VARCHAR(20) DEFAULT 'cod'"),
    ('orders', 'subtotal', 'DECIMAL(10,2) NULL'),
    ('orders', 'discount', 'DECIMAL(10,2) NOT NULL DEFAULT 0'),
    ('orders', 'shipping_fee', 'DECIMAL(10,2) NOT NULL DEFAULT 0'),
    ('orders', 'promo_code', 'VARCHAR(40) NULL'),
    ('orders', 'courier', 'VARCHAR(100) NULL'),
    ('orders', 'tracking_number', 'VARCHAR(100) NULL'),
    ('orders', 'processing_at', 'DATETIME NULL'),
    ('orders', 'shipped_at', 'DATETIME NULL'),
    ('orders', 'delivered_at', 'DATETIME NULL'),
    ('orders', 'cancelled_at', 'DATETIME NULL'),
]

DEFAULT_BOOK = {
    'title': 'You Version 2: Creating a Better Life with the Six Phases of Software Development (Hardcover)',
    'author': 'Ollie G. Baldemor',
    'genre': 'Print',
    'price': Decimal('200.00'),
    'original_price': Decimal('250.00'),
    'stock': 100,
    'cover_image': '/assets/cover.jpg',
    'pages': 280,
    'publisher': 'Ollie G. Baldemor Publishing (2026)',
    'isbn': '978-971-9872-01-3',
    'description': ("Why do we constantly update our phone apps, computer operational systems, and databases, yet leave "
                    "our personal habits running on legacy code? Ollie G. Baldemor introduces an inspiring personal "
                    "development roadmap, showing how you can debug your mind and design a balanced, successful life "
                    "using the six core phases of software development."),
}


def _column_exists(cursor, table, column):
    cursor.execute(
        "SELECT COUNT(*) AS n FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
        (table, column))
    return cursor.fetchone()['n'] > 0


def init_db():
    """Create missing tables/columns and seed the minimum data the storefront needs."""
    conn = get_db_connection()
    if not conn:
        print("init_db: database unavailable, skipping schema setup.")
        return False
    cursor = conn.cursor(dictionary=True)
    try:
        for statement in SCHEMA:
            cursor.execute(statement)
        for table, column, definition in COLUMN_UPGRADES:
            if not _column_exists(cursor, table, column):
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

        # Older databases: allow guest checkout and large inline covers
        cursor.execute(
            "SELECT IS_NULLABLE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = 'orders' AND COLUMN_NAME = 'buyer_id'")
        if cursor.fetchone()['IS_NULLABLE'] == 'NO':
            cursor.execute("ALTER TABLE orders MODIFY buyer_id INT NULL")
        cursor.execute(
            "SELECT DATA_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = 'books' AND COLUMN_NAME = 'cover_image'")
        if cursor.fetchone()['DATA_TYPE'] != 'longtext':
            cursor.execute("ALTER TABLE books MODIFY cover_image LONGTEXT")

        cursor.execute("UPDATE orders SET reference = CONCAT('YV-', LPAD(id, 6, '0')) WHERE reference IS NULL")
        cursor.execute("UPDATE orders SET subtotal = total_amount WHERE subtotal IS NULL")
        cursor.execute("UPDATE users SET team_role = 'admin' WHERE role = 'seller' AND team_role IS NULL")

        cursor.execute("SELECT COUNT(*) AS n FROM store_settings")
        if cursor.fetchone()['n'] == 0:
            cursor.execute("INSERT INTO store_settings (id, store_name, contact_email) VALUES (1, %s, %s)",
                           ('YouVersion 2 Store', 'olliebaldemor@lifeinversions.com'))

        # A store needs at least one seller account. It is created with a random password;
        # the owner sets a real one through "Forgot password".
        cursor.execute("SELECT id FROM users WHERE role = 'seller' ORDER BY id LIMIT 1")
        seller = cursor.fetchone()
        if not seller:
            seller_email = os.environ.get('SELLER_EMAIL', 'olliebaldemor@lifeinversions.com')
            cursor.execute("SELECT id FROM users WHERE email = %s", (seller_email,))
            existing = cursor.fetchone()
            if existing:
                cursor.execute("UPDATE users SET role = 'seller', team_role = 'admin' WHERE id = %s", (existing['id'],))
                seller_id = existing['id']
            else:
                random_pw = bcrypt.hashpw(secrets.token_urlsafe(24).encode(), bcrypt.gensalt()).decode()
                cursor.execute(
                    "INSERT INTO users (fname, mname, lname, email, password, role, team_role, is_verified) "
                    "VALUES ('Ollie', 'G.', 'Baldemor', %s, %s, 'seller', 'admin', 1)",
                    (seller_email, random_pw))
                seller_id = cursor.lastrowid
                print(f"init_db: created seller account {seller_email}. Use 'Forgot password' to set its password.")
        else:
            seller_id = seller['id']

        cursor.execute("SELECT COUNT(*) AS n FROM books")
        if cursor.fetchone()['n'] == 0:
            b = DEFAULT_BOOK
            cursor.execute(
                "INSERT INTO books (seller_id, title, description, author, genre, price, original_price, stock, "
                "cover_image, pages, publisher, isbn, is_featured) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1)",
                (seller_id, b['title'], b['description'], b['author'], b['genre'], b['price'], b['original_price'],
                 b['stock'], b['cover_image'], b['pages'], b['publisher'], b['isbn']))
        conn.commit()
        return True
    except mysql.connector.Error as err:
        conn.rollback()
        print(f"init_db failed: {err}")
        return False
    finally:
        cursor.close()
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def clean(value, max_len=255):
    if value is None:
        return None
    value = str(value).strip()
    return value[:max_len] if value else None


def to_json(row):
    """Make DB rows JSON-friendly (Decimals -> float, datetimes -> ISO strings)."""
    if row is None:
        return None
    out = {}
    for key, value in row.items():
        if isinstance(value, Decimal):
            out[key] = float(value)
        elif isinstance(value, (datetime, date)):
            out[key] = value.isoformat()
        else:
            out[key] = value
    return out


def generate_code():
    return ''.join(random.choices(string.digits, k=6))


def code_is_valid(user, code):
    if not user or not code or not user.get('verification_code'):
        return False
    if str(user['verification_code']) != str(code).strip():
        return False
    expires = user.get('code_expires_at')
    return expires is None or expires >= datetime.now()


def public_user(user):
    return {
        'id': user['id'],
        'fname': user['fname'],
        'mname': user.get('mname'),
        'lname': user['lname'],
        'extension': user.get('extension'),
        'email': user['email'],
        'role': user['role'],
        'team_role': user.get('team_role'),
        'profile_image': user.get('profile_image'),
    }


def normalize_cover(path):
    """Store covers as site-absolute paths so they resolve from any page depth."""
    if not path:
        return '/assets/cover.jpg'
    path = str(path)
    if path.startswith(('http://', 'https://', 'data:', '/')):
        return path
    while path.startswith('../'):
        path = path[3:]
    return '/' + path


def save_image_data_url(data_url, folder):
    """Persist a base64 data URL upload and return its public path."""
    match = re.match(r'^data:(image/[a-zA-Z+.-]+);base64,(.+)$', data_url, re.S)
    if not match:
        raise ApiError('Invalid image data.')
    mime, payload = match.group(1).lower(), match.group(2)
    if mime not in ALLOWED_IMAGE_TYPES:
        raise ApiError('Only JPG, PNG, WEBP or GIF images are allowed.')
    try:
        raw = base64.b64decode(payload, validate=False)
    except (ValueError, TypeError):
        raise ApiError('Invalid image data.')
    if len(raw) > MAX_IMAGE_BYTES:
        raise ApiError('Image is too large (max 5MB).', 413)
    target_dir = os.path.join(UPLOAD_DIR, folder)
    os.makedirs(target_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.{ALLOWED_IMAGE_TYPES[mime]}"
    with open(os.path.join(target_dir, filename), 'wb') as f:
        f.write(raw)
    return f"/uploads/{folder}/{filename}"


def resolve_cover(value):
    if value and str(value).startswith('data:'):
        return save_image_data_url(value, 'covers')
    return normalize_cover(value)


def client_ip():
    forwarded = request.headers.get('X-Forwarded-For', '')
    return (forwarded.split(',')[0].strip() or request.remote_addr or '')[:64]


def log_activity(cursor, user_id, action):
    cursor.execute("INSERT INTO activity_log (user_id, action, ip_address) VALUES (%s, %s, %s)",
                   (user_id, action[:255], client_ip()))


def notify_sellers(cursor, ntype, title, body_text, link):
    cursor.execute("SELECT id FROM users WHERE role = 'seller'")
    for row in cursor.fetchall():
        cursor.execute("INSERT INTO notifications (user_id, type, title, body, link) VALUES (%s,%s,%s,%s,%s)",
                       (row['id'], ntype, title[:255], body_text, link))


# ─────────────────────────────────────────────────────────────────────────────
# Authentication (signed session cookie set at login)
# ─────────────────────────────────────────────────────────────────────────────
def current_user():
    uid = session.get('uid')
    if not uid:
        return None
    with db() as (_, cursor):
        cursor.execute("SELECT * FROM users WHERE id = %s", (uid,))
        user = cursor.fetchone()
    if not user:
        session.clear()
    return user


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            raise ApiError('Please log in to continue.', 401)
        request.user = user
        return fn(*args, **kwargs)
    return wrapper


def self_required(fn):
    """The route's <user_id> must be the logged-in user."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            raise ApiError('Please log in to continue.', 401)
        if user['id'] != kwargs.get('user_id'):
            raise ApiError('You can only manage your own account.', 403)
        request.user = user
        return fn(*args, **kwargs)
    return wrapper


def seller_required(permission=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                raise ApiError('Please log in to continue.', 401)
            if user['role'] != 'seller':
                raise ApiError('Seller access required.', 403)
            allowed = TEAM_PERMISSIONS.get(user.get('team_role') or 'admin', set())
            if permission and permission not in allowed:
                raise ApiError('Your team role does not have access to this.', 403)
            request.user = user
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def recent_otp_ok():
    stamp = session.get('otp_verified_at')
    if not stamp:
        return False
    return datetime.now() - datetime.fromisoformat(stamp) <= timedelta(minutes=OTP_GRACE_MINUTES)


# ─────────────────────────────────────────────────────────────────────────────
# Account: signup, verification, password reset, login
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/signup', methods=['POST'])
def signup():
    data = body()
    fname = clean(data.get('fname'), 100)
    mname = clean(data.get('mname'), 100)
    lname = clean(data.get('lname'), 100)
    extension = clean(data.get('extension'), 20)
    email = (clean(data.get('email')) or '').lower()
    password = data.get('password') or ''
    role = 'buyer'  # Force role to buyer as requested

    # Address fields
    region = clean(data.get('region'), 100)
    province = clean(data.get('province'), 100)
    city = clean(data.get('city'), 100)
    barangay = clean(data.get('barangay'), 100)
    zipcode = clean(data.get('zipcode'), 20)
    street = clean(data.get('street'))
    house_number = clean(data.get('house_number'), 50)

    if not all([fname, lname, email, password]):
        raise ApiError('All fields are required.')
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        raise ApiError('Please enter a valid email address.')
    if len(password) < 8:
        raise ApiError('Password must be at least 8 characters long.')

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    verification_code = generate_code()
    expires = datetime.now() + timedelta(minutes=CODE_TTL_MINUTES)

    with db() as (_, cursor):
        cursor.execute("SELECT id, is_verified FROM users WHERE email = %s", (email,))
        existing = cursor.fetchone()
        if existing and existing['is_verified']:
            raise ApiError('Email already exists.', 409)
        values = (fname, mname, lname, extension, hashed_password, role, region, province, city, barangay,
                  zipcode, street, house_number, verification_code, expires)
        if existing:
            # An unverified signup can be retried (e.g. the code expired)
            cursor.execute(
                """UPDATE users SET fname=%s, mname=%s, lname=%s, extension=%s, password=%s, role=%s, region=%s,
                   province=%s, city=%s, barangay=%s, zipcode=%s, street=%s, house_number=%s,
                   verification_code=%s, code_expires_at=%s WHERE id=%s""", values + (existing['id'],))
            user_id = existing['id']
            cursor.execute("DELETE FROM user_addresses WHERE user_id = %s", (user_id,))
        else:
            cursor.execute(
                """INSERT INTO users (fname, mname, lname, extension, password, role, region, province, city,
                   barangay, zipcode, street, house_number, verification_code, code_expires_at, email, is_verified)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0)""", values + (email,))
            user_id = cursor.lastrowid
        if street or city:
            full_street = ' '.join(p for p in [house_number, street] if p)
            cursor.execute(
                """INSERT INTO user_addresses (user_id, street, barangay, city, province, zipcode, country, is_default)
                   VALUES (%s,%s,%s,%s,%s,%s,'PH',1)""", (user_id, full_street, barangay, city, province, zipcode))

    send_email(email, 'Verify your YouVersion2 Account', f"Your verification code is: {verification_code}")
    return jsonify({'message': 'User registered successfully! Please verify your email.', 'email': email}), 201


@app.route('/verify-email', methods=['POST'])
def verify_email():
    data = body()
    email = (clean(data.get('email')) or '').lower()
    code = clean(data.get('code'), 10)
    if not email or not code:
        raise ApiError('Email and verification code are required.')

    with db() as (_, cursor):
        cursor.execute("SELECT id, verification_code, code_expires_at FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if not code_is_valid(user, code):
            raise ApiError('Invalid or expired verification code.')
        cursor.execute("UPDATE users SET is_verified = 1, verification_code = NULL, code_expires_at = NULL "
                       "WHERE id = %s", (user['id'],))
    return jsonify({'message': 'Email verified successfully!'}), 200


@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    email = (clean(body().get('email')) or '').lower()
    if not email:
        raise ApiError('Email is required.')

    with db() as (_, cursor):
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if not user:
            raise ApiError('No account found with that email.', 404)
        verification_code = generate_code()
        cursor.execute("UPDATE users SET verification_code = %s, code_expires_at = %s WHERE id = %s",
                       (verification_code, datetime.now() + timedelta(minutes=CODE_TTL_MINUTES), user['id']))

    send_email(email, 'Reset your YouVersion2 Password', f"Your password reset code is: {verification_code}")
    return jsonify({'message': 'Password reset code sent to your email.'}), 200


@app.route('/verify-forgot-password-otp', methods=['POST'])
def verify_forgot_password_otp():
    data = body()
    email = (clean(data.get('email')) or '').lower()
    code = clean(data.get('code'), 10)
    if not email or not code:
        raise ApiError('Email and verification code are required.')
    with db() as (_, cursor):
        cursor.execute("SELECT verification_code, code_expires_at FROM users WHERE email = %s", (email,))
        if not code_is_valid(cursor.fetchone(), code):
            raise ApiError('Invalid or expired verification code.')
    return jsonify({'message': 'OTP verified successfully!'}), 200


@app.route('/reset-password', methods=['POST'])
def reset_password():
    data = body()
    email = (clean(data.get('email')) or '').lower()
    code = clean(data.get('code'), 10)
    new_password = data.get('password') or ''
    if not email or not code or not new_password:
        raise ApiError('Email, code, and new password are required.')
    if len(new_password) < 8:
        raise ApiError('Password must be at least 8 characters long.')

    with db() as (_, cursor):
        cursor.execute("SELECT id, verification_code, code_expires_at FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if not code_is_valid(user, code):
            raise ApiError('Invalid or expired verification code.')
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        # Receiving the code by email also proves ownership, so the account becomes verified
        cursor.execute("UPDATE users SET password = %s, verification_code = NULL, code_expires_at = NULL, "
                       "is_verified = 1 WHERE id = %s", (hashed_password, user['id']))
        log_activity(cursor, user['id'], 'Password reset via email code')
    return jsonify({'message': 'Password reset successfully!'}), 200


@app.route('/login', methods=['POST'])
def login():
    data = body()
    email = (clean(data.get('email')) or '').lower()
    password = data.get('password') or ''
    if not email or not password:
        raise ApiError('Email and password are required.')

    with db() as (_, cursor):
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            raise ApiError('Invalid email or password.', 401)
        if not user.get('is_verified'):
            raise ApiError('Please verify your email before logging in.', 403)
        if user['role'] == 'seller' and user.get('invite_status') == 'pending':
            cursor.execute("UPDATE users SET invite_status = 'active' WHERE id = %s", (user['id'],))
        if user['role'] == 'seller':
            log_activity(cursor, user['id'], 'Logged in')

    session.clear()
    session.permanent = True
    session['uid'] = user['id']
    return jsonify({'message': 'Login successful!', 'user': public_user(user)}), 200


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out.'}), 200


@app.route('/api/me', methods=['GET'])
def me():
    user = current_user()
    if not user:
        return jsonify({'user': None}), 200
    return jsonify({'user': public_user(user)}), 200


# ─────────────────────────────────────────────────────────────────────────────
# User profile, avatar, addresses, security
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/user/<int:user_id>', methods=['GET'])
@self_required
def get_user_profile(user_id):
    with db() as (_, cursor):
        cursor.execute("SELECT id, fname, mname, lname, extension, email, role, profile_image, bio, phone, "
                       "display_name FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise ApiError('User not found.', 404)
        cursor.execute("SELECT * FROM user_addresses WHERE user_id = %s ORDER BY is_default DESC, id", (user_id,))
        user['addresses'] = cursor.fetchall()
    return jsonify(user), 200


@app.route('/api/user/<int:user_id>', methods=['PUT'])
@self_required
def update_user_profile(user_id):
    data = body()
    fname = clean(data.get('fname'), 100)
    lname = clean(data.get('lname'), 100)
    if not fname or not lname:
        raise ApiError('First and last name are required.')
    with db() as (_, cursor):
        cursor.execute(
            "UPDATE users SET fname=%s, mname=%s, lname=%s, extension=%s, display_name=%s, phone=%s, bio=%s "
            "WHERE id=%s",
            (fname, clean(data.get('mname'), 100), lname, clean(data.get('extension'), 20),
             clean(data.get('display_name'), 120), clean(data.get('phone'), 40), clean(data.get('bio'), 2000),
             user_id))
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
    return jsonify({'message': 'Profile updated successfully!', 'user': public_user(user)}), 200


@app.route('/api/user/<int:user_id>/avatar', methods=['POST'])
@self_required
def upload_avatar(user_id):
    if 'avatar' not in request.files:
        raise ApiError('No file part')
    file = request.files['avatar']
    if file.filename == '':
        raise ApiError('No selected file')
    if file.mimetype not in ALLOWED_IMAGE_TYPES:
        raise ApiError('Only JPG, PNG, WEBP or GIF images are allowed.')
    filename = f"user_{user_id}_{uuid.uuid4().hex[:8]}_{secure_filename(file.filename)}"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file.save(os.path.join(UPLOAD_DIR, filename))
    url_path = f"/uploads/{filename}"

    with db() as (_, cursor):
        cursor.execute("UPDATE users SET profile_image = %s WHERE id = %s", (url_path, user_id))
    return jsonify({'message': 'Profile image updated successfully!', 'profile_image': url_path}), 200


@app.route('/api/user/<int:user_id>/address', methods=['POST'])
@self_required
def add_user_address(user_id):
    data = body()
    is_default = 1 if str(data.get('is_default', 0)) in ('1', 'true', 'True') else 0
    with db() as (_, cursor):
        cursor.execute("SELECT COUNT(*) AS n FROM user_addresses WHERE user_id = %s", (user_id,))
        if cursor.fetchone()['n'] == 0:
            is_default = 1  # the first address is always the default
        if is_default:
            cursor.execute("UPDATE user_addresses SET is_default = 0 WHERE user_id = %s", (user_id,))
        cursor.execute(
            """INSERT INTO user_addresses (user_id, street, barangay, city, province, zipcode, country, is_default)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (user_id, clean(data.get('street')), clean(data.get('barangay'), 100), clean(data.get('city'), 100),
             clean(data.get('province'), 100), clean(data.get('zipcode'), 20), clean(data.get('country'), 10) or 'PH',
             is_default))
    return jsonify({'message': 'Address added successfully!'}), 201


@app.route('/api/user/<int:user_id>/address/<int:address_id>', methods=['DELETE'])
@self_required
def delete_user_address(user_id, address_id):
    with db() as (_, cursor):
        cursor.execute("SELECT is_default FROM user_addresses WHERE user_id = %s AND id = %s", (user_id, address_id))
        address = cursor.fetchone()
        if not address:
            raise ApiError('Address not found.', 404)
        cursor.execute("DELETE FROM user_addresses WHERE user_id = %s AND id = %s", (user_id, address_id))
        if address['is_default']:
            cursor.execute("UPDATE user_addresses SET is_default = 1 WHERE user_id = %s ORDER BY id LIMIT 1",
                           (user_id,))
    return jsonify({'message': 'Address deleted successfully!'}), 200


@app.route('/api/user/<int:user_id>/address/<int:address_id>/default', methods=['PUT'])
@self_required
def set_default_address(user_id, address_id):
    with db() as (_, cursor):
        cursor.execute("SELECT id FROM user_addresses WHERE user_id = %s AND id = %s", (user_id, address_id))
        if not cursor.fetchone():
            raise ApiError('Address not found.', 404)
        cursor.execute("UPDATE user_addresses SET is_default = 0 WHERE user_id = %s", (user_id,))
        cursor.execute("UPDATE user_addresses SET is_default = 1 WHERE user_id = %s AND id = %s", (user_id, address_id))
    return jsonify({'message': 'Default address updated successfully!'}), 200


@app.route('/api/user/<int:user_id>/send_otp', methods=['POST'])
@self_required
def send_otp(user_id):
    # Can optionally provide an email to send to, otherwise we use the user's current email
    target_email = (clean(body().get('email')) or '').lower() or request.user['email']
    verification_code = generate_code()
    with db() as (_, cursor):
        cursor.execute("UPDATE users SET verification_code = %s, code_expires_at = %s WHERE id = %s",
                       (verification_code, datetime.now() + timedelta(minutes=CODE_TTL_MINUTES), user_id))
    session['otp_email'] = target_email
    session.pop('otp_verified_at', None)
    send_email(target_email, 'Security Verification - YouVersion2', f"Your verification code is: {verification_code}")
    return jsonify({'message': 'OTP sent successfully'}), 200


@app.route('/api/user/<int:user_id>/verify_otp', methods=['POST'])
@self_required
def verify_otp(user_id):
    code = clean(body().get('code'), 10)
    if not code:
        raise ApiError('Code is required')
    with db() as (_, cursor):
        cursor.execute("SELECT verification_code, code_expires_at FROM users WHERE id = %s", (user_id,))
        if not code_is_valid(cursor.fetchone(), code):
            raise ApiError('Invalid verification code')
        # Clear the code after successful verification
        cursor.execute("UPDATE users SET verification_code = NULL, code_expires_at = NULL WHERE id = %s", (user_id,))
    session['otp_verified_at'] = datetime.now().isoformat()
    return jsonify({'message': 'Verified successfully'}), 200


@app.route('/api/user/<int:user_id>/verify_password', methods=['POST'])
@self_required
def verify_password(user_id):
    password = body().get('password')
    if not password:
        raise ApiError('Password is required')
    if not bcrypt.checkpw(password.encode('utf-8'), request.user['password'].encode('utf-8')):
        raise ApiError('Incorrect current password', 401)
    return jsonify({'message': 'Password verified successfully'}), 200


@app.route('/api/user/<int:user_id>/password', methods=['PUT'])
@self_required
def update_password(user_id):
    data = body()
    new_password = data.get('password') or ''
    current = data.get('current_password')
    if len(new_password) < 8:
        raise ApiError('Password must be at least 8 characters long.')
    # Changing the password needs either the current password or a just-verified email code
    if current:
        if not bcrypt.checkpw(current.encode('utf-8'), request.user['password'].encode('utf-8')):
            raise ApiError('Incorrect current password', 401)
    elif not recent_otp_ok():
        raise ApiError('Please verify the code sent to your email first.', 403)

    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    with db() as (_, cursor):
        cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_password, user_id))
        log_activity(cursor, user_id, 'Password changed')
    session.pop('otp_verified_at', None)
    return jsonify({'message': 'Password updated successfully!'}), 200


@app.route('/api/user/<int:user_id>/email', methods=['PUT'])
@self_required
def update_email(user_id):
    new_email = (clean(body().get('email')) or '').lower()
    if not new_email:
        raise ApiError('Email is required')
    if not recent_otp_ok():
        raise ApiError('Please verify the code sent to your email first.', 403)
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', new_email):
        raise ApiError('Please enter a valid email address.')
    try:
        with db() as (_, cursor):
            cursor.execute("UPDATE users SET email = %s WHERE id = %s", (new_email, user_id))
    except mysql.connector.IntegrityError:
        raise ApiError('Email already exists.', 409)
    session.pop('otp_verified_at', None)
    return jsonify({'message': 'Email updated successfully!'}), 200


# ─────────────────────────────────────────────────────────────────────────────
# Books
# ─────────────────────────────────────────────────────────────────────────────
BOOK_SELECT = """
    SELECT b.*, COALESCE(r.avg_rating, 0) AS rating, COALESCE(r.review_count, 0) AS reviews_count
    FROM books b
    LEFT JOIN (SELECT book_id, AVG(rating) AS avg_rating, COUNT(*) AS review_count
               FROM reviews GROUP BY book_id) r ON r.book_id = b.id
"""


def serialize_book(row):
    book = to_json(row)
    book['cover_image'] = normalize_cover(book.get('cover_image'))
    book['rating'] = round(float(book.get('rating') or 0), 2)
    book['reviews_count'] = int(book.get('reviews_count') or 0)
    book['is_featured'] = bool(book.get('is_featured'))
    return book


def read_book_payload(data, partial=False):
    fields = {}
    for key, max_len in (('title', 255), ('author', 100), ('genre', 100), ('publisher', 255), ('isbn', 40)):
        if key in data or not partial:
            fields[key] = clean(data.get(key), max_len)
    if 'description' in data or not partial:
        fields['description'] = clean(data.get('description'), 20000)
    for key in ('price', 'original_price'):
        if key in data or not partial:
            raw = data.get(key)
            if raw in (None, ''):
                fields[key] = None
            else:
                try:
                    value = Decimal(str(raw)).quantize(Decimal('0.01'))
                except Exception:
                    raise ApiError(f'Invalid {key.replace("_", " ")}.')
                if value < 0:
                    raise ApiError('Prices cannot be negative.')
                fields[key] = value
    for key in ('stock', 'pages'):
        if key in data or not partial:
            raw = data.get(key)
            if raw in (None, ''):
                fields[key] = 0 if key == 'stock' else None
            else:
                try:
                    fields[key] = max(0, int(raw))
                except (TypeError, ValueError):
                    raise ApiError(f'Invalid {key}.')
    if 'cover_image' in data or not partial:
        fields['cover_image'] = resolve_cover(data.get('cover_image'))
    if not partial and not all([fields.get('title'), fields.get('author'), fields.get('price') is not None]):
        raise ApiError('Missing required fields.')
    if fields.get('original_price') is not None and fields.get('price') is not None \
            and fields['original_price'] <= fields['price']:
        fields['original_price'] = None
    return fields


@app.route('/books', methods=['POST'])
@seller_required('books')
def add_book():
    fields = read_book_payload(body())
    fields['seller_id'] = request.user['id']
    columns = ', '.join(fields)
    placeholders = ', '.join(['%s'] * len(fields))
    with db() as (_, cursor):
        cursor.execute(f"INSERT INTO books ({columns}) VALUES ({placeholders})", tuple(fields.values()))
        book_id = cursor.lastrowid
        log_activity(cursor, request.user['id'], f"Published book: {fields['title']}")
    return jsonify({'message': 'Book added successfully!', 'id': book_id}), 201


@app.route('/books', methods=['GET'])
def get_books():
    seller_id = request.args.get('seller_id')
    query = BOOK_SELECT + " WHERE b.is_active = 1"
    params = []
    if seller_id:
        query += " AND b.seller_id = %s"
        params.append(seller_id)
    query += " ORDER BY b.is_featured DESC, b.created_at DESC"
    with db() as (_, cursor):
        cursor.execute(query, params)
        books = [serialize_book(b) for b in cursor.fetchall()]
    return jsonify(books), 200


@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    with db() as (_, cursor):
        cursor.execute(BOOK_SELECT + " WHERE b.id = %s AND b.is_active = 1", (book_id,))
        book = cursor.fetchone()
    if not book:
        raise ApiError('Book not found.', 404)
    return jsonify(serialize_book(book)), 200


@app.route('/books/<int:book_id>', methods=['PUT'])
@seller_required('books')
def update_book(book_id):
    fields = read_book_payload(body(), partial=True)
    if not fields:
        raise ApiError('Nothing to update.')
    if 'title' in fields and not fields['title']:
        raise ApiError('Title is required.')
    if 'price' in fields and fields['price'] is None:
        raise ApiError('Price is required.')
    assignments = ', '.join(f"{k} = %s" for k in fields)
    with db() as (_, cursor):
        cursor.execute("SELECT id, title FROM books WHERE id = %s AND is_active = 1", (book_id,))
        book = cursor.fetchone()
        if not book:
            raise ApiError('Book not found.', 404)
        cursor.execute(f"UPDATE books SET {assignments} WHERE id = %s", tuple(fields.values()) + (book_id,))
        log_activity(cursor, request.user['id'], f"Edited book: {fields.get('title') or book['title']}")
    return jsonify({'message': 'Book updated successfully!'}), 200


@app.route('/books/<int:book_id>', methods=['DELETE'])
@seller_required('books')
def delete_book(book_id):
    # Soft delete keeps past orders intact
    with db() as (_, cursor):
        cursor.execute("SELECT title FROM books WHERE id = %s AND is_active = 1", (book_id,))
        book = cursor.fetchone()
        if not book:
            raise ApiError('Book not found.', 404)
        cursor.execute("UPDATE books SET is_active = 0, is_featured = 0 WHERE id = %s", (book_id,))
        log_activity(cursor, request.user['id'], f"Deleted book: {book['title']}")
    return jsonify({'message': 'Book deleted successfully!'}), 200


@app.route('/api/seller/books/<int:book_id>/feature', methods=['POST'])
@seller_required('books')
def feature_book(book_id):
    with db() as (_, cursor):
        cursor.execute("SELECT id FROM books WHERE id = %s AND is_active = 1", (book_id,))
        if not cursor.fetchone():
            raise ApiError('Book not found.', 404)
        # Unfeature all books, then feature the specific book
        cursor.execute("UPDATE books SET is_featured = 0")
        cursor.execute("UPDATE books SET is_featured = 1 WHERE id = %s", (book_id,))
    return jsonify({'message': 'Book featured successfully'})


@app.route('/api/featured-book', methods=['GET'])
def get_featured_book():
    with db() as (_, cursor):
        cursor.execute(BOOK_SELECT + " WHERE b.is_featured = 1 AND b.is_active = 1 LIMIT 1")
        book = cursor.fetchone()
    return jsonify({'book': serialize_book(book) if book else None})


# ─────────────────────────────────────────────────────────────────────────────
# Orders
# ─────────────────────────────────────────────────────────────────────────────
def _new_reference(cursor):
    while True:
        reference = f"YV-{random.randint(100000, 999999)}"
        cursor.execute("SELECT 1 FROM orders WHERE reference = %s", (reference,))
        if not cursor.fetchone():
            return reference


def _load_order(cursor, order_id):
    cursor.execute("""SELECT o.*, u.fname AS buyer_fname, u.lname AS buyer_lname, u.email AS buyer_email,
                             u.phone AS buyer_phone
                      FROM orders o LEFT JOIN users u ON u.id = o.buyer_id WHERE o.id = %s""", (order_id,))
    order = cursor.fetchone()
    if not order:
        return None
    cursor.execute("""SELECT oi.id, oi.book_id, oi.quantity, oi.price, b.title, b.author, b.cover_image
                      FROM order_items oi JOIN books b ON b.id = oi.book_id WHERE oi.order_id = %s""", (order_id,))
    items = []
    for item in cursor.fetchall():
        item = to_json(item)
        item['cover_image'] = normalize_cover(item['cover_image'])
        item['line_total'] = round(item['price'] * item['quantity'], 2)
        items.append(item)
    order = to_json(order)
    order['items'] = items
    order['item_count'] = sum(i['quantity'] for i in items)
    order['customer_name'] = ' '.join(filter(None, [order.get('ship_fname'), order.get('ship_lname')])) or \
        ' '.join(filter(None, [order.get('buyer_fname'), order.get('buyer_lname')])) or 'Guest'
    order['customer_email'] = order.get('ship_email') or order.get('buyer_email')
    return order


@app.route('/api/orders', methods=['POST'])
def create_order():
    data = body()
    shipping = data.get('shipping') or {}
    items = data.get('items') or []
    required = {k: clean(shipping.get(k)) for k in ('fname', 'lname', 'email', 'address', 'city', 'zip')}
    if not all(required.values()):
        raise ApiError('Please complete all shipping fields.')
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', required['email']):
        raise ApiError('Please enter a valid email address.')
    payment_method = data.get('payment_method') if data.get('payment_method') in ('cod', 'ewallet') else 'cod'
    if not isinstance(items, list) or not items:
        raise ApiError('Your cart is empty.')

    quantities = {}
    for item in items:
        try:
            book_id, qty = int(item.get('book_id')), int(item.get('quantity'))
        except (TypeError, ValueError, AttributeError):
            raise ApiError('Invalid cart item.')
        if qty < 1:
            raise ApiError('Invalid quantity.')
        quantities[book_id] = quantities.get(book_id, 0) + qty
    if any(q > MAX_QTY_PER_TITLE for q in quantities.values()):
        raise ApiError(f'Maximum of {MAX_QTY_PER_TITLE} copies per title.')

    user = current_user()
    buyer_id = user['id'] if user else None
    promo = (clean(data.get('promo_code'), 40) or '').upper() or None
    if promo and promo not in PROMO_CODES:
        raise ApiError('Invalid promo code.')

    with db() as (_, cursor):
        placeholders = ', '.join(['%s'] * len(quantities))
        # Lock the rows so concurrent checkouts can't oversell stock
        cursor.execute(f"SELECT id, title, price, stock FROM books WHERE is_active = 1 AND id IN ({placeholders}) "
                       "FOR UPDATE", tuple(quantities))
        books = {b['id']: b for b in cursor.fetchall()}
        missing = [bid for bid in quantities if bid not in books]
        if missing:
            raise ApiError('Some items in your cart are no longer available. Please refresh your cart.', 409)
        for bid, qty in quantities.items():
            if books[bid]['stock'] < qty:
                left = books[bid]['stock']
                raise ApiError(f'Only {left} cop{"y" if left == 1 else "ies"} of "{books[bid]["title"]}" left in stock.',
                               409)

        subtotal = sum(books[bid]['price'] * qty for bid, qty in quantities.items())
        discount = (subtotal * PROMO_CODES[promo]).quantize(Decimal('0.01')) if promo else Decimal('0.00')
        shipping_fee = Decimal('0.00') if subtotal - discount >= FREE_SHIPPING_THRESHOLD else SHIPPING_FEE
        total = subtotal - discount + shipping_fee
        reference = _new_reference(cursor)

        cursor.execute(
            """INSERT INTO orders (buyer_id, total_amount, status, reference, ship_fname, ship_lname, ship_email,
               ship_address, ship_city, ship_zip, payment_method, subtotal, discount, shipping_fee, promo_code)
               VALUES (%s,%s,'Pending',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (buyer_id, total, reference, required['fname'], required['lname'], required['email'], required['address'],
             required['city'], required['zip'], payment_method, subtotal, discount, shipping_fee, promo))
        order_id = cursor.lastrowid
        for bid, qty in quantities.items():
            cursor.execute("INSERT INTO order_items (order_id, book_id, quantity, price) VALUES (%s,%s,%s,%s)",
                           (order_id, bid, qty, books[bid]['price']))
            cursor.execute("UPDATE books SET stock = stock - %s WHERE id = %s", (qty, bid))
        notify_sellers(cursor, 'order', 'New Order Received',
                       f"{required['fname']} {required['lname']} placed order #{reference} (₱{total:,.2f}).",
                       f"seller-order-details.html?id={order_id}")

    estimated = (datetime.now() + timedelta(days=2)).date().isoformat()
    lines = '\n'.join(f"- {books[bid]['title']} x{qty}" for bid, qty in quantities.items())
    send_email(required['email'], f'Order #{reference} confirmed - YouVersion 2',
               f"Hi {required['fname']},\n\nThank you for your order!\n\n{lines}\n\nTotal: PHP {total:,.2f}\n"
               f"Payment: {'Cash on Delivery' if payment_method == 'cod' else 'E-Wallet on delivery'}\n"
               f"Estimated delivery: {estimated}\n")
    return jsonify({'message': 'Order placed successfully!', 'order': {
        'id': order_id, 'reference': reference, 'total': float(total), 'subtotal': float(subtotal),
        'discount': float(discount), 'shipping_fee': float(shipping_fee), 'estimated_delivery': estimated}}), 201


@app.route('/api/orders', methods=['GET'])
@login_required
def list_orders():
    user = request.user
    status = request.args.get('status')
    query = """SELECT o.id FROM orders o"""
    clauses, params = [], []
    if user['role'] == 'seller':
        if 'orders' not in TEAM_PERMISSIONS.get(user.get('team_role') or 'admin', set()):
            raise ApiError('Your team role does not have access to this.', 403)
    else:
        clauses.append("o.buyer_id = %s")
        params.append(user['id'])
    if status and status in ORDER_STATUSES:
        clauses.append("o.status = %s")
        params.append(status)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY o.created_at DESC, o.id DESC"
    with db() as (_, cursor):
        cursor.execute(query, params)
        ids = [row['id'] for row in cursor.fetchall()]
        orders = [_load_order(cursor, oid) for oid in ids]
    return jsonify(orders), 200


@app.route('/api/orders/<int:order_id>', methods=['GET'])
@login_required
def get_order(order_id):
    with db() as (_, cursor):
        order = _load_order(cursor, order_id)
    if not order:
        raise ApiError('Order not found.', 404)
    user = request.user
    if user['role'] != 'seller' and order.get('buyer_id') != user['id']:
        raise ApiError('Order not found.', 404)
    return jsonify(order), 200


@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
@seller_required('orders')
def update_order_status(order_id):
    data = body()
    new_status = data.get('status')
    if new_status not in ORDER_STATUSES:
        raise ApiError('Invalid status.')
    courier = clean(data.get('courier'), 100)
    tracking = clean(data.get('tracking_number'), 100)
    if new_status == 'Shipped' and (not courier or not tracking):
        raise ApiError('Courier and tracking number are required to ship an order.')

    flow = {'Pending': {'Processing', 'Shipped', 'Cancelled'},
            'Processing': {'Shipped', 'Cancelled'},
            'Shipped': {'Delivered'},
            'Delivered': set(), 'Cancelled': set()}
    with db() as (_, cursor):
        cursor.execute("SELECT * FROM orders WHERE id = %s FOR UPDATE", (order_id,))
        order = cursor.fetchone()
        if not order:
            raise ApiError('Order not found.', 404)
        if new_status not in flow.get(order['status'], set()):
            raise ApiError(f"An order that is {order['status']} cannot be marked {new_status}.", 409)
        stamp_column = {'Processing': 'processing_at', 'Shipped': 'shipped_at',
                        'Delivered': 'delivered_at', 'Cancelled': 'cancelled_at'}[new_status]
        if new_status == 'Shipped':
            cursor.execute(f"UPDATE orders SET status=%s, courier=%s, tracking_number=%s, {stamp_column}=NOW(), "
                           "processing_at = COALESCE(processing_at, NOW()) WHERE id=%s",
                           (new_status, courier, tracking, order_id))
        else:
            cursor.execute(f"UPDATE orders SET status=%s, {stamp_column}=NOW() WHERE id=%s", (new_status, order_id))
        if new_status == 'Cancelled':
            cursor.execute("""UPDATE books b JOIN order_items oi ON oi.book_id = b.id
                              SET b.stock = b.stock + oi.quantity WHERE oi.order_id = %s""", (order_id,))
        log_activity(cursor, request.user['id'], f"Order #{order['reference']} marked {new_status}")

    recipient = order.get('ship_email')
    if recipient and (new_status != 'Shipped' or data.get('notify_customer', True)):
        message = f"Your order #{order['reference']} is now {new_status}."
        if new_status == 'Shipped':
            message += f"\nCourier: {courier}\nTracking number: {tracking}"
        send_email(recipient, f"Order #{order['reference']} update - YouVersion 2", message)
    return jsonify({'message': f'Order marked as {new_status}.'}), 200


# ─────────────────────────────────────────────────────────────────────────────
# Seller dashboard
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/seller/stats', methods=['GET'])
@seller_required()
def seller_stats():
    with db() as (_, cursor):
        cursor.execute("""SELECT COALESCE(SUM(total_amount), 0) AS revenue, COUNT(*) AS orders,
                                 COUNT(DISTINCT COALESCE(CAST(buyer_id AS CHAR), ship_email)) AS customers
                          FROM orders WHERE status <> 'Cancelled'""")
        totals = cursor.fetchone()
        cursor.execute("""SELECT COALESCE(SUM(oi.quantity), 0) AS sold FROM order_items oi
                          JOIN orders o ON o.id = oi.order_id WHERE o.status <> 'Cancelled'""")
        sold = cursor.fetchone()['sold']
        cursor.execute("SELECT COUNT(*) AS n FROM orders WHERE status IN ('Pending', 'Processing', 'Shipped')")
        active = cursor.fetchone()['n']
        cursor.execute("SELECT COUNT(*) AS n FROM orders WHERE status = 'Pending'")
        pending = cursor.fetchone()['n']
        cursor.execute("SELECT COALESCE(AVG(rating), 0) AS avg, COUNT(*) AS n, "
                       "SUM(reply IS NULL) AS unanswered FROM reviews")
        reviews = cursor.fetchone()
        cursor.execute("SELECT COUNT(*) AS n FROM books WHERE is_active = 1")
        titles = cursor.fetchone()['n']

        # Books sold per month for the last 6 months (including empty months)
        cursor.execute("""SELECT DATE_FORMAT(o.created_at, '%Y-%m') AS ym, SUM(oi.quantity) AS sold,
                                 SUM(oi.quantity * oi.price) AS sales
                          FROM orders o JOIN order_items oi ON oi.order_id = o.id
                          WHERE o.status <> 'Cancelled' AND o.created_at >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
                          GROUP BY ym""")
        by_month = {row['ym']: row for row in cursor.fetchall()}
        months = []
        cursor_date = date.today().replace(day=1)
        for _ in range(6):
            months.append(cursor_date)
            cursor_date = (cursor_date - timedelta(days=1)).replace(day=1)
        months.reverse()
        monthly = [{'label': m.strftime('%b'), 'month': m.strftime('%B %Y'),
                    'sold': int(by_month.get(m.strftime('%Y-%m'), {}).get('sold') or 0),
                    'sales': float(by_month.get(m.strftime('%Y-%m'), {}).get('sales') or 0)} for m in months]

        cursor.execute("""SELECT ship_city AS city, COUNT(*) AS n FROM orders
                          WHERE status <> 'Cancelled' AND ship_city IS NOT NULL
                          GROUP BY ship_city ORDER BY n DESC LIMIT 5""")
        cities = [to_json(r) for r in cursor.fetchall()]
        cursor.execute("SELECT id FROM orders ORDER BY created_at DESC, id DESC LIMIT 5")
        recent = [_load_order(cursor, row['id']) for row in cursor.fetchall()]
        cursor.execute("SELECT COUNT(*) AS n FROM notifications WHERE user_id = %s AND is_read = 0",
                       (request.user['id'],))
        unread = cursor.fetchone()['n']

    return jsonify({
        'revenue': float(totals['revenue']), 'orders': totals['orders'], 'customers': totals['customers'],
        'books_sold': int(sold), 'active_orders': active, 'pending_orders': pending,
        'avg_rating': round(float(reviews['avg']), 2), 'review_count': reviews['n'],
        'unanswered_reviews': int(reviews['unanswered'] or 0), 'titles': titles,
        'monthly': monthly, 'cities': cities, 'recent_orders': recent, 'unread_notifications': unread,
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# Reviews
# ─────────────────────────────────────────────────────────────────────────────
REVIEW_SELECT = """SELECT r.*, u.fname, u.lname, u.profile_image, b.title AS book_title
                   FROM reviews r JOIN users u ON u.id = r.buyer_id JOIN books b ON b.id = r.book_id"""


@app.route('/api/books/<int:book_id>/reviews', methods=['GET'])
def get_book_reviews(book_id):
    with db() as (_, cursor):
        cursor.execute(REVIEW_SELECT + " WHERE r.book_id = %s ORDER BY r.created_at DESC", (book_id,))
        reviews = [to_json(r) for r in cursor.fetchall()]
    return jsonify(reviews), 200


@app.route('/api/books/<int:book_id>/reviews', methods=['POST'])
@login_required
def post_review(book_id):
    data = body()
    try:
        rating = int(data.get('rating'))
    except (TypeError, ValueError):
        rating = 0
    if rating < 1 or rating > 5:
        raise ApiError('Please choose a rating from 1 to 5 stars.')
    comment = clean(data.get('comment'), 4000)
    if not comment:
        raise ApiError('Please write a short review.')
    user = request.user
    with db() as (_, cursor):
        cursor.execute("SELECT title FROM books WHERE id = %s AND is_active = 1", (book_id,))
        book = cursor.fetchone()
        if not book:
            raise ApiError('Book not found.', 404)
        cursor.execute("SELECT id FROM reviews WHERE book_id = %s AND buyer_id = %s", (book_id, user['id']))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("UPDATE reviews SET rating=%s, comment=%s, created_at=NOW() WHERE id=%s",
                           (rating, comment, existing['id']))
            review_id = existing['id']
        else:
            cursor.execute("INSERT INTO reviews (book_id, buyer_id, rating, comment) VALUES (%s,%s,%s,%s)",
                           (book_id, user['id'], rating, comment))
            review_id = cursor.lastrowid
        notify_sellers(cursor, 'review', f"New {rating}-Star Review!",
                       f"{user['fname']} {user['lname']} reviewed {book['title']}: \"{comment[:80]}\"",
                       f"seller-reply-review.html?id={review_id}")
    return jsonify({'message': 'Thanks for your review!', 'id': review_id}), 201


@app.route('/api/reviews', methods=['GET'])
@seller_required('reviews')
def list_reviews():
    rating = request.args.get('rating')
    query, params = REVIEW_SELECT, []
    if rating and rating.isdigit():
        query += " WHERE r.rating = %s"
        params.append(int(rating))
    query += " ORDER BY r.created_at DESC"
    with db() as (_, cursor):
        cursor.execute(query, params)
        reviews = [to_json(r) for r in cursor.fetchall()]
        cursor.execute("SELECT rating, COUNT(*) AS n FROM reviews GROUP BY rating")
        breakdown = {str(i): 0 for i in range(1, 6)}
        for row in cursor.fetchall():
            breakdown[str(row['rating'])] = row['n']
        cursor.execute("SELECT COALESCE(AVG(rating), 0) AS avg, COUNT(*) AS n FROM reviews")
        summary = cursor.fetchone()
    return jsonify({'reviews': reviews, 'breakdown': breakdown,
                    'average': round(float(summary['avg']), 1), 'total': summary['n']}), 200


@app.route('/api/reviews/<int:review_id>', methods=['GET'])
@seller_required('reviews')
def get_review(review_id):
    with db() as (_, cursor):
        cursor.execute(REVIEW_SELECT + " WHERE r.id = %s", (review_id,))
        review = cursor.fetchone()
    if not review:
        raise ApiError('Review not found.', 404)
    return jsonify(to_json(review)), 200


@app.route('/api/reviews/<int:review_id>/reply', methods=['PUT'])
@seller_required('reviews')
def reply_review(review_id):
    reply = clean(body().get('reply'), 4000)
    if not reply:
        raise ApiError('Reply cannot be empty.')
    with db() as (_, cursor):
        cursor.execute("SELECT id FROM reviews WHERE id = %s", (review_id,))
        if not cursor.fetchone():
            raise ApiError('Review not found.', 404)
        cursor.execute("UPDATE reviews SET reply = %s, replied_at = NOW() WHERE id = %s", (reply, review_id))
        log_activity(cursor, request.user['id'], f"Replied to review #{review_id}")
    return jsonify({'message': 'Reply posted publicly.'}), 200


@app.route('/api/reviews/<int:review_id>/helpful', methods=['POST'])
def mark_review_helpful(review_id):
    voted = set(session.get('helpful_votes', []))
    if review_id in voted:
        raise ApiError('You already marked this review as helpful.', 409)
    with db() as (_, cursor):
        cursor.execute("UPDATE reviews SET helpful_count = helpful_count + 1 WHERE id = %s", (review_id,))
        if cursor.rowcount == 0:
            raise ApiError('Review not found.', 404)
        cursor.execute("SELECT helpful_count FROM reviews WHERE id = %s", (review_id,))
        count = cursor.fetchone()['helpful_count']
    session['helpful_votes'] = list(voted | {review_id})
    return jsonify({'helpful_count': count}), 200


# ─────────────────────────────────────────────────────────────────────────────
# Notifications
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/notifications', methods=['GET'])
@login_required
def list_notifications():
    with db() as (_, cursor):
        cursor.execute("SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC, id DESC LIMIT 100",
                       (request.user['id'],))
        items = [to_json(n) for n in cursor.fetchall()]
    return jsonify({'notifications': items, 'unread': sum(1 for n in items if not n['is_read'])}), 200


@app.route('/api/notifications/read-all', methods=['POST'])
@login_required
def read_all_notifications():
    with db() as (_, cursor):
        cursor.execute("UPDATE notifications SET is_read = 1 WHERE user_id = %s", (request.user['id'],))
    return jsonify({'message': 'All notifications marked as read.'}), 200


@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def read_notification(notification_id):
    with db() as (_, cursor):
        cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = %s AND user_id = %s",
                       (notification_id, request.user['id']))
    return jsonify({'message': 'Marked as read.'}), 200


# ─────────────────────────────────────────────────────────────────────────────
# Store settings, team & activity
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/store', methods=['GET'])
def get_store():
    with db() as (_, cursor):
        cursor.execute("SELECT store_name, contact_email FROM store_settings WHERE id = 1")
        store = cursor.fetchone() or {'store_name': 'YouVersion 2 Store', 'contact_email': None}
    return jsonify(store), 200


@app.route('/api/store', methods=['PUT'])
@seller_required('store')
def update_store():
    data = body()
    name = clean(data.get('store_name'))
    email = clean(data.get('contact_email'))
    if not name:
        raise ApiError('Store name is required.')
    if email and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        raise ApiError('Please enter a valid contact email.')
    with db() as (_, cursor):
        cursor.execute("UPDATE store_settings SET store_name = %s, contact_email = %s WHERE id = 1", (name, email))
        log_activity(cursor, request.user['id'], 'Updated store profile')
    return jsonify({'message': 'Store profile saved.'}), 200


@app.route('/api/seller/team', methods=['GET'])
@seller_required()
def list_team():
    with db() as (_, cursor):
        cursor.execute("SELECT id, fname, lname, email, profile_image, team_role, invite_status FROM users "
                       "WHERE role = 'seller' ORDER BY id")
        team = cursor.fetchall()
    return jsonify({'team': team, 'me': request.user['id']}), 200


@app.route('/api/seller/team', methods=['POST'])
@seller_required('team')
def invite_team_member():
    data = body()
    full_name = clean(data.get('name'), 200)
    email = (clean(data.get('email')) or '').lower()
    team_role = data.get('team_role')
    if not full_name or not email or team_role not in TEAM_PERMISSIONS:
        raise ApiError('Name, email and role are required.')
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        raise ApiError('Please enter a valid email address.')
    parts = full_name.split()
    fname, lname = parts[0], ' '.join(parts[1:]) or '-'
    temp_password = secrets.token_urlsafe(9)
    hashed = bcrypt.hashpw(temp_password.encode(), bcrypt.gensalt()).decode()
    with db() as (_, cursor):
        cursor.execute("SELECT id, role FROM users WHERE email = %s", (email,))
        existing = cursor.fetchone()
        if existing and existing['role'] == 'seller':
            raise ApiError('That person is already on the team.', 409)
        if existing:
            # Promote an existing buyer account; they keep their own password
            cursor.execute("UPDATE users SET role = 'seller', team_role = %s, invite_status = 'pending' WHERE id = %s",
                           (team_role, existing['id']))
            temp_password = None
        else:
            cursor.execute(
                "INSERT INTO users (fname, lname, email, password, role, team_role, invite_status, is_verified) "
                "VALUES (%s, %s, %s, %s, 'seller', %s, 'pending', 1)", (fname, lname, email, hashed, team_role))
        log_activity(cursor, request.user['id'], f"Invited {full_name} as {team_role}")

    login_url = request.host_url.rstrip('/') + '/login.html'
    message = (f"Hi {fname},\n\n{request.user['fname']} {request.user['lname']} invited you to manage the "
               f"YouVersion 2 store as {team_role}.\n\nLog in at {login_url} with this email.")
    if temp_password:
        message += f"\nTemporary password: {temp_password}\nPlease change it in Settings after logging in."
    send_email(email, "You're invited to the YouVersion 2 seller team", message)
    return jsonify({'message': f'Invitation sent to {email}.'}), 201


@app.route('/api/seller/team/<int:member_id>', methods=['PUT'])
@seller_required('team')
def update_team_member(member_id):
    team_role = body().get('team_role')
    if team_role not in TEAM_PERMISSIONS:
        raise ApiError('Invalid role.')
    if member_id == request.user['id'] and team_role != 'admin':
        raise ApiError('You cannot remove your own admin access.', 409)
    with db() as (_, cursor):
        cursor.execute("UPDATE users SET team_role = %s WHERE id = %s AND role = 'seller'", (team_role, member_id))
        if cursor.rowcount == 0:
            cursor.execute("SELECT id FROM users WHERE id = %s AND role = 'seller'", (member_id,))
            if not cursor.fetchone():
                raise ApiError('Team member not found.', 404)
        log_activity(cursor, request.user['id'], f"Changed team member #{member_id} role to {team_role}")
    return jsonify({'message': 'Role updated.'}), 200


@app.route('/api/seller/team/<int:member_id>', methods=['DELETE'])
@seller_required('team')
def remove_team_member(member_id):
    if member_id == request.user['id']:
        raise ApiError('You cannot remove yourself from the team.', 409)
    with db() as (_, cursor):
        cursor.execute("SELECT fname, lname FROM users WHERE id = %s AND role = 'seller'", (member_id,))
        member = cursor.fetchone()
        if not member:
            raise ApiError('Team member not found.', 404)
        # Their books stay with the store; the account becomes a regular buyer account
        cursor.execute("UPDATE users SET role = 'buyer', team_role = NULL WHERE id = %s", (member_id,))
        cursor.execute("UPDATE books SET seller_id = %s WHERE seller_id = %s", (request.user['id'], member_id))
        log_activity(cursor, request.user['id'], f"Removed {member['fname']} {member['lname']} from the team")
    return jsonify({'message': 'Team member removed.'}), 200


@app.route('/api/seller/activity', methods=['GET'])
@seller_required('team')
def activity():
    try:
        limit = min(100, max(1, int(request.args.get('limit', 10))))
    except ValueError:
        limit = 10
    with db() as (_, cursor):
        cursor.execute("""SELECT a.action, a.ip_address, a.created_at, u.fname, u.lname
                          FROM activity_log a LEFT JOIN users u ON u.id = a.user_id
                          ORDER BY a.created_at DESC, a.id DESC LIMIT %s""", (limit,))
        rows = [to_json(r) for r in cursor.fetchall()]
    return jsonify(rows), 200


# ─────────────────────────────────────────────────────────────────────────────
# Buyer ↔ seller messaging
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/chat', methods=['POST'])
@login_required
def send_chat():
    data = body()
    message = clean(data.get('message'), 4000)
    user = request.user
    if not message:
        raise ApiError('Message cannot be empty.')
    with db() as (_, cursor):
        if user['role'] == 'seller':
            if 'messages' not in TEAM_PERMISSIONS.get(user.get('team_role') or 'admin', set()):
                raise ApiError('Your team role does not have access to this.', 403)
            buyer_id, seller_id, sender = data.get('buyer_id'), user['id'], 'seller'
            cursor.execute("SELECT id FROM users WHERE id = %s", (buyer_id,))
            if not cursor.fetchone():
                raise ApiError('Buyer not found.', 404)
        else:
            buyer_id, seller_id, sender = user['id'], data.get('seller_id'), 'buyer'
            cursor.execute("SELECT id FROM users WHERE id = %s AND role = 'seller'", (seller_id,))
            if not cursor.fetchone():
                raise ApiError('Seller not found.', 404)
        cursor.execute("INSERT INTO chats (buyer_id, seller_id, sender, message) VALUES (%s, %s, %s, %s)",
                       (buyer_id, seller_id, sender, message))
        if sender == 'buyer':
            cursor.execute("INSERT INTO notifications (user_id, type, title, body, link) VALUES (%s,'message',%s,%s,%s)",
                           (seller_id, f"New message from {user['fname']} {user['lname']}", message[:200],
                            f"seller-messages.html?buyer_id={buyer_id}"))
    return jsonify({'success': True}), 201


@app.route('/api/chat/<int:buyer_id>/<int:seller_id>', methods=['GET'])
@login_required
def get_chat_history(buyer_id, seller_id):
    if request.user['id'] not in (buyer_id, seller_id):
        raise ApiError('You are not part of this conversation.', 403)
    with db() as (_, cursor):
        cursor.execute("SELECT * FROM chats WHERE buyer_id = %s AND seller_id = %s ORDER BY created_at ASC, id ASC",
                       (buyer_id, seller_id))
        chats = [to_json(c) for c in cursor.fetchall()]
    return jsonify(chats), 200


@app.route('/api/chat/conversations/<int:user_id>/<string:role>', methods=['GET'])
@self_required
def get_conversations(user_id, role):
    if role not in ('buyer', 'seller'):
        raise ApiError('Invalid role.')
    with db() as (_, cursor):
        if role == 'seller':
            # Distinct buyers who chatted with this seller
            cursor.execute("""SELECT u.id, u.fname, u.lname, u.profile_image, MAX(c.created_at) AS last_time
                              FROM chats c JOIN users u ON c.buyer_id = u.id WHERE c.seller_id = %s
                              GROUP BY u.id, u.fname, u.lname, u.profile_image ORDER BY last_time DESC""", (user_id,))
        else:
            # Distinct sellers who this buyer chatted with
            cursor.execute("""SELECT u.id, u.fname, u.lname, u.profile_image, MAX(c.created_at) AS last_time
                              FROM chats c JOIN users u ON c.seller_id = u.id WHERE c.buyer_id = %s
                              GROUP BY u.id, u.fname, u.lname, u.profile_image ORDER BY last_time DESC""", (user_id,))
        conversations = [to_json(c) for c in cursor.fetchall()]
        for conv in conversations:
            pair = (conv['id'], user_id) if role == 'seller' else (user_id, conv['id'])
            cursor.execute("SELECT message FROM chats WHERE buyer_id = %s AND seller_id = %s "
                           "ORDER BY created_at DESC, id DESC LIMIT 1", pair)
            last_msg = cursor.fetchone()
            conv['last_message'] = last_msg['message'] if last_msg else None
    return jsonify(conversations), 200


@app.route('/api/sellers/default', methods=['GET'])
def default_seller():
    """The seller buyers should message when a book has no specific seller."""
    with db() as (_, cursor):
        cursor.execute("SELECT id, fname, lname FROM users WHERE role = 'seller' "
                       "ORDER BY team_role = 'admin' DESC, id LIMIT 1")
        seller = cursor.fetchone()
    if not seller:
        raise ApiError('No seller available.', 404)
    return jsonify(seller), 200


@app.route('/api/sellers/<int:seller_id>', methods=['GET'])
def seller_public(seller_id):
    """Public display name of a seller, for starting a conversation."""
    with db() as (_, cursor):
        cursor.execute("SELECT id, fname, lname, profile_image FROM users WHERE id = %s AND role = 'seller'",
                       (seller_id,))
        seller = cursor.fetchone()
    if not seller:
        raise ApiError('Seller not found.', 404)
    return jsonify(seller), 200


# ─────────────────────────────────────────────────────────────────────────────
# AI assistant (Gemini)
# ─────────────────────────────────────────────────────────────────────────────
# Cache FAQs globally to avoid disk I/O on every request
faqs_text = ""
try:
    with open(os.path.join(BASE_DIR, 'faqs.json'), 'r', encoding='utf-8') as f:
        faqs = json.load(f)
        faqs_text = "Here are the FAQs you can use to answer questions:\n"
        for item in faqs:
            faqs_text += f"Q: {item.get('question')}\nA: {item.get('answer')}\n\n"
except (OSError, ValueError):
    pass

# Initialize Gemini once globally
api_key_global = os.environ.get('GEMINI_API_KEY')
chat_model = None
if api_key_global and genai:
    genai.configure(api_key=api_key_global)
    chat_model = genai.GenerativeModel(os.environ.get('GEMINI_MODEL', 'gemini-flash-latest'))


@app.route('/api/ai-chat', methods=['POST'])
def ai_chat():
    message = clean(body().get('message'), 2000)
    if not message:
        raise ApiError('Message is required')
    if not chat_model:
        raise ApiError('The AI assistant is not configured (missing GEMINI_API_KEY).', 503)

    def generate():
        # Force Werkzeug/Flask to flush headers and start stream immediately
        yield " " * 1024
        try:
            prompt = (f"You are a helpful bookstore AI assistant named 'YV2 AI'. Respond politely and concisely to "
                      f"the following user message.\n\n{faqs_text}\n\nUser: {message}")
            response = chat_model.generate_content(prompt, stream=True)
            for chunk in response:
                yield chunk.text
        except Exception as e:
            print(f"AI chat error: {e}")
            yield "\nSorry, I couldn't reach the assistant right now. Please try again in a moment."

    resp = Response(stream_with_context(generate()), mimetype='text/plain')
    resp.headers['X-Accel-Buffering'] = 'no'
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


# ─────────────────────────────────────────────────────────────────────────────
# Static site — only public front-end files are served (never source, SQL or .env)
# ─────────────────────────────────────────────────────────────────────────────
PUBLIC_EXTENSIONS = {'.html', '.css', '.js', '.json', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico',
                     '.woff', '.woff2', '.txt'}
PRIVATE_FILES = {'buyer-home-gen.js', 'fix_links.js', 'fix_settings_link.js', 'organize.js', 'requirements.txt'}


@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')


@app.route('/<path:path>')
def send_static(path):
    parts = path.replace('\\', '/').split('/')
    ext = os.path.splitext(path)[1].lower()
    if (any(p.startswith('.') or p == '__pycache__' for p in parts) or ext not in PUBLIC_EXTENSIONS
            or parts[-1] in PRIVATE_FILES):
        abort(404)
    if path.startswith('api/'):
        abort(404)
    return send_from_directory(BASE_DIR, path)


@app.errorhandler(404)
def not_found(err):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found.'}), 404
    return err


@app.errorhandler(405)
def method_not_allowed(err):
    if request.path.startswith('/api/') or request.method != 'GET':
        return jsonify({'error': 'Method not allowed.'}), 405
    return err


# Create/upgrade tables when the app starts (works under gunicorn too)
init_db()

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', port=int(os.environ.get('PORT', 5000)))
