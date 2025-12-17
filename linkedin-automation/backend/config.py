import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
AGIOPEN_API_KEY = os.getenv('AGIOPEN_API_KEY') or os.getenv('OAGI_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAIIMAGE_API_KEY = os.getenv('OPENAIIMAGE_API_KEY')

# Set OAGI environment variables for SDK
if AGIOPEN_API_KEY:
    os.environ['OAGI_API_KEY'] = AGIOPEN_API_KEY
os.environ['OAGI_BASE_URL'] = "https://api.agiopen.org"

# API URLs
AGIOPEN_API_URL = "https://api.agiopen.org/v1/lux"
OPENAI_IMAGE_API_URL = "https://api.openai.com/v1/images/generations"

# Database
DATABASE_URL = "sqlite:///linkedin_automation.db"

# App config
FLASK_PORT = 5001
FRONTEND_URL = "http://localhost:8080"  # Your Vite dev server port

# LinkedIn Profile URL (for sharing posts)
LINKEDIN_PROFILE_URL = os.getenv('LINKEDIN_PROFILE_URL', 'https://www.linkedin.com/in/junhyun-kim-15840128b/')

# CORS - Allow multiple common dev ports
ALLOWED_ORIGINS = [
    "http://localhost:8080",
    "http://localhost:8081", 
    "http://localhost:3000",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:8081",
    "http://127.0.0.1:3000"
]

