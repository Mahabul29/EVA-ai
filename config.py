"""
EvaAI Chat - Configuration (Gemini API)
"""
import os

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'eva-ai-secret-key-change-in-production')
    
    # CORS settings for cross-origin access (Koyeb deployment)
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')
    
    # Google Gemini API Configuration
    # Get your free API key from: https://aistudio.google.com/app/apikey
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    GEMINI_API_URL = os.environ.get('GEMINI_API_URL', 'https://generativelanguage.googleapis.com/v1beta/models/')
    
    # Default model - Gemini 2.5 Flash (free tier: 1500 requests/day)
    # Other free options: gemini-2.5-flash-lite, gemini-3.1-flash-lite
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')
    
    # App settings
    MAX_HISTORY = int(os.environ.get('MAX_HISTORY', '20'))
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    PORT = int(os.environ.get('PORT', '8000'))
