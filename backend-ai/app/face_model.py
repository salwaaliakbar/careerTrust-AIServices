from pymongo import MongoClient
import numpy as np

# Initialize MongoDB client and collection
client = MongoClient('mongodb://localhost:27017/')
db = client['careerTrust']
coll = db['face_embeddings']

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