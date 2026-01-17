import os
from dotenv import load_dotenv

# Load environment variables from .env file in project root
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
