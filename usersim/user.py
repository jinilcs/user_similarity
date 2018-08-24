from flask import Flask, request
from flask import jsonify
from flask import Response
import numpy as np
import sqlite3
from sklearn.metrics.pairwise import cosine_similarity
import heapq
from cache import LRUCache

app = Flask(__name__)
db_file = '../db/usersim.sqlite'
cache = LRUCache(capacity=50)
users_cache_size = 100
sql_batch_size = 1000

def send_error(message, status):
    """
    To send an error response to client
    """
    data = {}
    data['error_text'] = message
    data['users'] = []
    response = jsonify(data)
    response.status_code = status
    return response

@app.route('/similarusers/<int:user_handle>')
def get_similar_users(user_handle):
    """
    Returns the list of similar users in a json format
    
    Parameters
    ----------
    user_handle : int value, mandatory
        Unique identifier for a user. 
    
    num_users : int value, optional
        Number of similar users in the result
    
    Returns
    ----------
    JSON response, which has error code, error text, status, 
    and list of similar users. 
    Sample response:
    {"error":0,"error_text":"","users":[6744,8740], "status":200}
    """
    num_users = request.args.get('numusers')
    if num_users:
        try:
            num_users = int(num_users)
        except:
            num_users = 10
    else:
        num_users = 10
    minheap = []
    conn = None
    cur = None
    
    similar_users = {}
    
    if num_users <= users_cache_size:
        is_found, user_list = cache.lookup(user_handle)
        if is_found:
            similar_users['users'] = user_list[:num_users]
            return jsonify(similar_users)
    
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute('select * from users where user_handle=?', (str(user_handle),))  
        input_user = cur.fetchone()
        if not input_user:
            return send_error('User handle is not found', 404)
    
        input_user = np.array(input_user).reshape(1,-1)[:,1:]
        cur.execute('select * from users')
        fetch_size = max(num_users, users_cache_size) + 1
        users = cur.fetchmany(fetch_size)
        if not users:
            return user_not_found('No similar users', 404)
        
        users = np.array(users)
        user_ids = users[:,0]
        users = users[:,1:]
        
        similarities = cosine_similarity(input_user, users)[0]
        
        for user_id, sim in zip(user_ids, similarities):
            if user_id != user_handle:
                minheap.append((sim, int(user_id)))
        
        heapq.heapify(minheap)

        while True:
            users = cur.fetchmany(sql_batch_size)
            if not users:
                break
                
            users = np.array(users)
            user_ids = users[:,0]
            users = users[:,1:]
            similarities = cosine_similarity(input_user, users)[0]

            for user_id, sim in zip(user_ids, similarities):
                if user_id != user_handle:
                    heapq.heappushpop(minheap, (sim, int(user_id)))
        
    except Exception as e:
        return send_error(str(e), 500)
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()
    
    user_list = [s[1] for s in heapq.nlargest(fetch_size-1, minheap)]
    cache.insert(user_handle, user_list[:users_cache_size])
    similar_users['users'] = user_list[:num_users]
    return jsonify(similar_users)

if __name__ == "__main__":
        app.run(host='0.0.0.0', port=9080)

