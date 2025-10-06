from pymongo import MongoClient
import os
from datetime import datetime
from Models.exam import Exam
from dotenv import load_dotenv
from bson import ObjectId

load_dotenv()
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
client = MongoClient(MONGO_URI)
db = client['be_db']
exams_collection = db['exams']

class ExamDbService:
    @staticmethod
    def create_exam(exam: Exam):
        exams_collection.insert_one(exam.to_dict())
        return True

    @staticmethod
    def get_exam_by_id(exam_id):
        try:
            obj_id = ObjectId(exam_id)
        except Exception:
            return None
        data = exams_collection.find_one({'_id': obj_id})
        if data:
            data['_id'] = str(data['_id'])
        return data

    @staticmethod
    def update_exam(exam_id, update_fields: dict):
        try:
            obj_id = ObjectId(exam_id)
        except Exception:
            return False
        result = exams_collection.update_one({'_id': obj_id}, {'$set': update_fields})
        return result.modified_count > 0

    @staticmethod
    def delete_exam(exam_id):
        try:
            obj_id = ObjectId(exam_id)
        except Exception:
            return False
        result = exams_collection.delete_one({'_id': obj_id})
        return result.deleted_count > 0

    @staticmethod
    def list_exams(filter_dict=None):
        filter_dict = filter_dict or {}
        docs = list(exams_collection.find(filter_dict))
        for doc in docs:
            doc['_id'] = str(doc['_id'])
        return docs
    
    @staticmethod
    def bulk_create_exams(exam_list):
        """Bulk insert multiple exams for better performance"""
        if exam_list:
            docs = [exam.to_dict() for exam in exam_list]
            result = exams_collection.insert_many(docs)
            return len(result.inserted_ids)
        return 0
    
    @staticmethod
    def get_exams_by_student(student_id, limit=100):
        """Get exams by student ID with limit"""
        return list(exams_collection.find(
            {'student_id': student_id}
        ).sort('created_at', -1).limit(limit))
    
    @staticmethod
    def get_exams_by_date_range(start_date, end_date):
        """Get exams within date range"""
        return list(exams_collection.find({
            'created_at': {
                '$gte': start_date,
                '$lte': end_date
            }
        }).sort('created_at', -1))
