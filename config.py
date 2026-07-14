"""
EvaAI Chat - Configuration
"""
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'eva-ai-secret-key-change-in-production')
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    GEMINI_API_URL = os.environ.get('GEMINI_API_URL', 'https://generativelanguage.googleapis.com/v1beta/models/')
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')
    MAX_HISTORY = int(os.environ.get('MAX_HISTORY', '20'))
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    PORT = int(os.environ.get('PORT', '8000'))
