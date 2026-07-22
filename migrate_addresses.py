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
        
        # Create user_addresses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `user_addresses` (
                `id` int(11) NOT NULL AUTO_INCREMENT,
                `user_id` int(11) NOT NULL,
                `street` varchar(255) DEFAULT NULL,
                `barangay` varchar(100) DEFAULT NULL,
                `city` varchar(100) DEFAULT NULL,
                `province` varchar(100) DEFAULT NULL,
                `zipcode` varchar(20) DEFAULT NULL,
                `country` varchar(10) DEFAULT 'PH',
                `is_default` tinyint(1) DEFAULT 0,
                PRIMARY KEY (`id`),
                FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        
        # Move existing addresses from users table to user_addresses
        cursor.execute("SELECT id, street, barangay, city, province, zipcode FROM users")
        users = cursor.fetchall()
        
        for user in users:
            uid, street, brgy, city, prov, zcode = user
            if any([street, brgy, city, prov, zcode]):
                # Check if address already exists for this user
                cursor.execute("SELECT id FROM user_addresses WHERE user_id = %s", (uid,))
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO user_addresses (user_id, street, barangay, city, province, zipcode, is_default)
                        VALUES (%s, %s, %s, %s, %s, %s, 1)
                    """, (uid, street, brgy, city, prov, zcode))
        
        conn.commit()
        print("Migration successful. user_addresses table created and data moved.")
            
    except mysql.connector.Error as err:
        print(f"Error migrating database: {err}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    migrate()
