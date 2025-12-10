# check_models.py
import os
from google import genai
from dotenv import load_dotenv

# Load your new key from .env
load_dotenv()

# Check if the key is loaded
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not found in .env")
    exit()

try:
    # Initialize the client with the new key
    client = genai.Client(api_key=api_key)

    print(f"✅ Success: Key connected. Listing models for: {client.project_name}\n")
    print("Available Models:")

    # List and filter the models
    model_names = [m.name for m in client.models.list() if "generateContent" in m.supported_actions]

    for name in model_names:
        print(f"- {name}")

except Exception as e:
    print(f"❌ Connection Error: {e}")
    print("A 403 error here means the key is invalid, revoked, or the location is unsupported.")