import os
from google_auth_oauthlib.flow import InstalledAppFlow

# 1. SETUP
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://mail.google.com/"
]

def main():
    print("--- 🔍 DIAGNOSTIC MODE STARTED ---")

    # 2. CHECK FOR CREDENTIALS FILE
    if not os.path.exists("credentials.json"):
        print("❌ CRITICAL ERROR: 'credentials.json' was not found!")
        print(f"   Current folder: {os.getcwd()}")
        print("   Please move the downloaded JSON file into this folder.")
        return

    print("✅ Found 'credentials.json'. Initializing Login...")
    print("-------------------------------------------------------")
    print("   Attempting to open browser... ")
    print("   IF BROWSER DOES NOT OPEN, LOOK FOR A LINK BELOW.")
    print("-------------------------------------------------------")

    try:
        # 3. START AUTH FLOW
        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json", SCOPES
        )
        
        # This will verify specific ports to avoid firewall blocks
        creds = flow.run_local_server(port=0)

        # 4. SAVE TOKEN
        with open("token.json", "w") as token:
            token.write(creds.to_json())
            
        print("\n\n🎉 SUCCESS! 'token.json' has been generated.")
        print("   You may now run: streamlit run genesis_ui.py")
        
    except Exception as e:
        print(f"\n❌ AUTH FAILED: {e}")

if __name__ == "__main__":
    main()