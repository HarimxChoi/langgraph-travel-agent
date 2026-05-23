"""Environment loading and client initialization."""

import os
from dotenv import load_dotenv
from amadeus import Client
from langchain_google_genai import ChatGoogleGenerativeAI
from twilio.rest import Client as TwilioClient

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.env'))

# Required keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")

# Optional keys
HOTELBEDS_API_KEY = os.getenv("HOTELBEDS_API_KEY")
HOTELBEDS_API_SECRET = os.getenv("HOTELBEDS_API_SECRET")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_SENDER_PHONE = os.getenv("TWILIO_SENDER_PHONE")
HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY")

if not all([GOOGLE_API_KEY, AMADEUS_API_KEY, AMADEUS_API_SECRET]):
    raise ValueError("Required API keys missing: GOOGLE_API_KEY, AMADEUS_API_KEY, AMADEUS_API_SECRET")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=GOOGLE_API_KEY,
)

amadeus = None
twilio_client = None

try:
    if AMADEUS_API_KEY and AMADEUS_API_SECRET:
        amadeus = Client(client_id=AMADEUS_API_KEY, client_secret=AMADEUS_API_SECRET)
        print("Amadeus client initialized")

    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        print("Twilio client initialized")
except Exception as e:
    print(f"Client initialization warning: {e}")
