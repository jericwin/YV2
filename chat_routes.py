
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
