from pymongo import MongoClient
import os
from Models.correctans import CorrectAns
from dotenv import load_dotenv
from bson import ObjectId

load_dotenv()
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
client = MongoClient(MONGO_URI)
db = client['be_db']
correctans_collection = db['correctans']


class CorrectAnsDbService:
    @staticmethod
    def create_correct_ans(correct_ans: CorrectAns):
        """Create new correct answer set"""
        result = correctans_collection.insert_one(correct_ans.to_dict())
        return str(result.inserted_id)

    @staticmethod
    def get_correct_ans_by_id(correctans_id):
        """Get correct answer by MongoDB _id"""
        try:
            obj_id = ObjectId(correctans_id)
        except Exception:
            return None
        data = correctans_collection.find_one({'_id': obj_id})
        if data:
            return CorrectAns(data['id'], data['answers'])
        return None

    @staticmethod
    def get_correct_ans_by_exam_code(exam_code):
        """Get correct answer by exam code"""
        data = correctans_collection.find_one({'id': str(exam_code)})
        if data:
            return CorrectAns(data['id'], data['answers'])
        return None

    @staticmethod
    def update_correct_ans(exam_code, answers: list):
        """Update or insert correct answer by exam code"""
        result = correctans_collection.update_one(
            {'id': str(exam_code)},
            {'$set': {'answers': answers}},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None

    @staticmethod
    def delete_correct_ans(exam_code):
        """Delete correct answer by exam code"""
        result = correctans_collection.delete_one({'id': str(exam_code)})
        return result.deleted_count > 0

    @staticmethod
    def list_all_correct_ans():
        """List all correct answer sets"""
        results = list(correctans_collection.find({}))
        return [CorrectAns(doc['id'], doc['answers']) for doc in results]

    @staticmethod
    def check_exists(exam_code):
        """Check if correct answer exists for exam code"""
        doc = correctans_collection.find_one({'id': str(exam_code)})
        return doc is not None
