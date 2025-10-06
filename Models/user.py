# models/user.py

from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
client = MongoClient(MONGO_URI)
db = client['be_db']
users_collection = db['users']

class User:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password

    def to_dict(self):
        return {'email': self.email, 'password': self.password}

    @staticmethod
    def find_by_email(email: str):
        data = users_collection.find_one({'email': email})
        if data:
            return User(data['email'], data['password'])
        return None

    @staticmethod
    def create(email: str, password: str):
        users_collection.insert_one({'email': email, 'password': password})
        return User(email, password)

