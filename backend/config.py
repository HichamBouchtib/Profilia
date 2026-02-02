import os
from datetime import timedelta, datetime, timezone

class Config:
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # File Upload
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', '16777216'))  # 16MB default
    
    # Claude AI
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    MODEL = os.environ.get('MODEL', 'claude-sonnet-4-20250514')
    PAGES_PER_CHUNK = int(os.environ.get('PAGES_PER_CHUNK', '1'))
    
    # Wait for documents upload
    WAIT_FOR_DOCS_SECONDS = int(os.environ.get('WAIT_FOR_DOCS_SECONDS', '60'))
    
    # CORS - Allow both localhost and Docker service names
    CORS_ORIGINS = [
        'http://localhost:3000', 
        'http://frontend:3000',
        'http://localhost:3001'  # In case of port conflicts
    ]
    
    # Leconomiste credentials
    LECONOMISTE_USERNAME = os.environ.get('LECONOMISTE_USERNAME')
    LECONOMISTE_PASSWORD = os.environ.get('LECONOMISTE_PASSWORD')
    
    # SerpAPI
    SERPAPI_API_KEY = os.environ.get('SERPAPI_API_KEY')

class DevelopmentConfig(Config):
    DEBUG = True
    FLASK_ENV = 'development'

class ProductionConfig(Config):
    DEBUG = False
    FLASK_ENV = 'production'
    
    # Override with production values
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',') if os.environ.get('CORS_ORIGINS') else [
        'http://localhost:3000', 
        'http://frontend:3000'
    ]

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
