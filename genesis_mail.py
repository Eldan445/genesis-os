import smtplib
import imaplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
import time
import os

# --- CONFIGURATION (The Keys to the Kingdom) ---
EMAIL_USER = "genesissystemos@gmail.com"  # <--- REPLACE THIS
EMAIL_PASS = "jwei vfcu vzev nibp"   # <--- USE YOUR APP PASSWORD HERE

# --- PART 1: THE MOUTH (Sending) ---
def send_email(to_email, subject, body):
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_USER
        msg['To'] = to_email
        
        server.send_message(msg)
        server.quit()
        return "✅ Email Sent."
    except Exception as e:
        return f"❌ Send Failed: {e}"

# --- PART 2: THE EYES (Reading) ---
def get_unread_emails():
    print("👀 Genesis is scanning Inbox...")
    unread_list = []
    
    try:
        # Connect to Gmail IMAP
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        # Search for unread emails (UNSEEN)
        status, messages = mail.search(None, "UNSEEN")
        email_ids = messages[0].split()

        if not email_ids:
            return "📭 No new messages."

        # Loop through the latest 3 unread emails
        for e_id in email_ids[-3:]: 
            # Fetch the email data
            res, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    # Parse the bytes into an email object
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Decode Subject
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    
                    # Decode Sender
                    sender = msg.get("From")
                    
                    unread_list.append(f"📩 FROM: {sender}\n   SUBJ: {subject}")
        
        mail.close()
        mail.logout()
        return "\n".join(unread_list)

    except Exception as e:
        return f"❌ Read Failed: {e}"

# --- PART 3: THE SENTRY (Notification Mode) ---
def monitor_inbox():
    print("🛡️ GENESIS SENTINEL MODE ACTIVE")
    print("   Scanning for new emails every 10 seconds...")
    print("   (Press Ctrl+C to stop)")
    
    previous_count = 0
    
    while True:
        try:
            # 1. Quick check for count only
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(EMAIL_USER, EMAIL_PASS)
            mail.select("inbox")
            status, messages = mail.search(None, "UNSEEN")
            current_count = len(messages[0].split()) if messages[0] else 0
            mail.logout()

            # 2. Logic
            if current_count > previous_count:
                print("\n🚨 NEW EMAIL DETECTED!")
                # Read the details
                details = get_unread_emails()
                print(details)
                
                # --- AUDIO NOTIFICATION (OPTIONAL) ---
                # If you want it to beep on Windows:
                import winsound
                winsound.Beep(1000, 500) # Frequency 1000Hz, 500ms
                
            elif current_count < previous_count:
                print("\nStart processing emails...")
            
            previous_count = current_count
            time.sleep(10) # Wait 10 seconds

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

# --- MASTER CONTROL ---
if __name__ == "__main__":
    choice = input("Select Mode: [1] Read Unread [2] Send Email [3] Monitor Live: ")
    
    if choice == "1":
        print(get_unread_emails())
    elif choice == "2":
        to = input("To: ")
        sub = input("Subject: ")
        bod = input("Body: ")
        print(send_email(to, sub, bod))
    elif choice == "3":
        monitor_inbox()