import os
from google_auth_oauthlib.flow import InstalledAppFlow

# DEFINING THE MASTER SCOPES (Read + Send + Calendar)
SCOPES = [
    "https://www.googleapis.com/auth/calendar",      # Full Calendar Access
    "https://mail.google.com/"                       # Full Gmail Access (Read & Send)
]

def main():
    print("--- 🔐 UPGRADING SECURITY CLEARANCE ---")
    
    # 1. Check for the Lock
    if not os.path.exists("credentials.json"):
        print("❌ ERROR: 'credentials.json' missing. Put it in this folder.")
        return

    # 2. Start the Auth Flow
    print("   Requesting Full Access (Read/Send)...")
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json", SCOPES
        )
        # Force a fresh login prompt
        creds = flow.run_local_server(port=0, prompt='consent') 

        # 3. Save the New Key
        with open("token.json", "w") as token:
            token.write(creds.to_json())
            
        print("\n✅ SUCCESS: New 'token.json' created with READ permissions.")
        print("   You may now run: streamlit run genesis_ui.py")
        
    except Exception as e:
        print(f"\n❌ FAILED: {e}")

if __name__ == "__main__":
    main()