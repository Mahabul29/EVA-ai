"""
EvaAI Chat - Configuration
"""
import os

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'eva-ai-secret-key-change-in-production')
    
    # CORS settings for cross-origin access (Koyeb deployment)
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')
    
    # AI API Configuration
    # Using Pollinations AI (free, no API key required)
    AI_API_URL = os.environ.get('AI_API_URL', 'https://text.pollinations.ai/')
    
    # Alternative: You can use OpenRouter, Groq, or any OpenAI-compatible API
    # Just set AI_API_URL and AI_API_KEY in environment variables
    AI_API_KEY = os.environ.get('AI_API_KEY', None)
    AI_MODEL = os.environ.get('AI_MODEL', 'openai')
    
    # App settings
    MAX_HISTORY = int(os.environ.get('MAX_HISTORY', '20'))
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    PORT = int(os.environ.get('PORT', '8000'))
