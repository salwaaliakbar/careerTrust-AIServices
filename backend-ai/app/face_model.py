from pymongo import MongoClient
import numpy as np
from app.db import client, db, coll

def get_all_embeddings():
    """
    Fetch all stored embeddings from MongoDB.
    Returns list of tuples: (user_id, embedding as np.array).
    """
    docs = coll.find({}, {'user_id': 1, 'embedding': 1})
    return [(doc['user_id'], np.array(doc['embedding'])) for doc in docs]

def add_embedding(user_id, embedding):
    """
    Add or update an embedding for a userId in MongoDB.
    Embedding must be a numpy array.
    """
    coll.update_one(
        {'user_id': user_id}, 
        {'$set': {'embedding': embedding.tolist()}}, 
        upsert=True
    )

def get_embedding_by_user(user_id):
    doc = coll.find_one({'user_id': user_id}, {'embedding': 1})
    if not doc or 'embedding' not in doc:
        return None
    return np.array(doc['embedding'])