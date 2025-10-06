# services/Auth/auth_service.py
import hashlib
from Models.user import User

class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def sign_up(email: str, password: str):
        if User.find_by_email(email):
            return {'error': 'User already exists'}
        hashed = AuthService.hash_password(password)
        user = User.create(email, hashed)
        return {'message': 'User created', 'user': user.to_dict()}

    @staticmethod
    def login(email: str, password: str):
        user = User.find_by_email(email)
        if not user:
            return {'error': 'Invalid credentials'}
        hashed = AuthService.hash_password(password)
        if user.password != hashed:
            return {'error': 'Invalid credentials'}
        return {'message': 'Login successful', 'user': user.to_dict()}

    @staticmethod
    def logout(email: str):
        # For demo, just return a message
        if not User.find_by_email(email):
            return {'error': 'User not found'}
        return {'message': 'Logout successful'}
