import mysql.connector

DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '',
    'database': 'yv2_db'
}

def migrate():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        columns = [
            ("is_verified", "TINYINT(1) NOT NULL DEFAULT 0"),
            ("verification_code", "VARCHAR(10) DEFAULT NULL")
        ]
        
        for col_name, col_type in columns:
            cursor.execute(f"SHOW COLUMNS FROM users LIKE '{col_name}'")
            if not cursor.fetchone():
                print(f"Adding '{col_name}' column...")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
        
        conn.commit()
        print("Migration successful. Verification columns added.")
            
    except mysql.connector.Error as err:
        print(f"Error migrating database: {err}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    migrate()
