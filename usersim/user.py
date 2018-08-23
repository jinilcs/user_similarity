from flask import Flask, request
from flask import jsonify
import numpy as np
import sqlite3
from sklearn.metrics.pairwise import cosine_similarity
import heapq

app = Flask(__name__)
db_file = '../db/usersim.sqlite'

@app.route('/simusers')
def get_similar_users():
    
    user_handle = request.args.get('userhandle')
    if not user_handle:
        return 'user not found'
    num_users = request.args.get('numusers')
    if not num_users:
        num_users=10
    else:
        num_users = int(num_users)
    
    minheap = []
    conn = None
    cur = None
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute('select * from users where user_handle=?', (str(user_handle),))  
        input_user = cur.fetchone()
        
        if not input_user:
            raise Exception('User Not Found')
    
        input_user = np.array(input_user).reshape(1,-1)[:,1:]
        
        cur.execute('select * from users')
        
        users = cur.fetchmany(num_users+1)
        if not users:
            return
        users = np.array(users)
        user_ids = users[:,0]
        users = users[:,1:]
        
        similarities = cosine_similarity(input_user, users)[0]
        
        for user_id, sim in zip(user_ids, similarities):
            if user_id != user_handle:
                minheap.append((sim, int(user_id)))
        
        heapq.heapify(minheap)
                
        while True:
            users = cur.fetchmany(1000)
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
        return str(e)
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()
    
    return jsonify([s[1] for s in heapq.nlargest(num_users, minheap)])

if __name__ == "__main__":
        app.run(host="0.0.0.0", port=9080)
