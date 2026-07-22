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
            ("region", "VARCHAR(100) DEFAULT NULL"),
            ("province", "VARCHAR(100) DEFAULT NULL"),
            ("city", "VARCHAR(100) DEFAULT NULL"),
            ("barangay", "VARCHAR(100) DEFAULT NULL"),
            ("zipcode", "VARCHAR(20) DEFAULT NULL"),
            ("street", "VARCHAR(255) DEFAULT NULL"),
            ("house_number", "VARCHAR(50) DEFAULT NULL")
        ]
        
        for col_name, col_type in columns:
            cursor.execute(f"SHOW COLUMNS FROM users LIKE '{col_name}'")
            if not cursor.fetchone():
                print(f"Adding '{col_name}' column...")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
        
        conn.commit()
        print("Migration successful. Address columns added.")
            
    except mysql.connector.Error as err:
        print(f"Error migrating database: {err}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    migrate()
