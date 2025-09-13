import os
from dotenv import load_dotenv

load_dotenv()

PORT = os.getenv("PORT", 6000)
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
SERVICE_OPERATOR_SID = os.getenv("SERVICE_OPERATOR_SID")
HUMAN_SERVICE_OPERATOR_SID = os.getenv("HUMAN_SERVICE_SID")

SERVICE_URL = os.getenv("SERVICE_URL")
WELCOME_GREETING = "Hello! Welcome to CoffeeMarket. How can I help you today?"

# Azure OpenAI Configuration
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
AZURE_API_KEY = os.getenv("AZURE_API_KEY")
AZURE_DEPLOYMENT = os.getenv("AZURE_DEPLOYMENT")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION")

ENABLE_STREAMING = os.getenv("ENABLE_STREAMING", "True").lower() == "true"