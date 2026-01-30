#!/usr/bin/env python3
"""
Script to send email with final CSV attached
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Email settings (from .env or GitHub secrets)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO")  # Boss email

# CSV file to be sent
CSV_FILE = PROJECT_ROOT / "data" / "Balancer-All-Tokenomics.csv"

# Email template
EMAIL_TEMPLATE = PROJECT_ROOT / "template" / "email_template.html"


def load_email_template() -> str:
    """
    Loads email HTML template and replaces placeholders.
    
    Returns:
        String with email HTML
    """
    if not EMAIL_TEMPLATE.exists():
        raise FileNotFoundError(f"Email template not found: {EMAIL_TEMPLATE}")
    
    # Read template
    html_content = EMAIL_TEMPLATE.read_text(encoding='utf-8')
    
    # Replace placeholders
    timestamp = datetime.now().strftime("%m/%d/%Y at %H:%M")
    html_content = html_content.replace("{{ timestamp }}", timestamp)
    
    return html_content


def send_email_with_csv(
    csv_file: Path = CSV_FILE,
    subject: str = None
):
    """
    Sends email with CSV attached.
    
    Args:
        csv_file: Path to CSV file
        subject: Email subject (optional)
    """
    print("=" * 60)
    print("📧 Sending Email with CSV")
    print("=" * 60)
    
    # Check settings
    if not EMAIL_FROM:
        raise ValueError("EMAIL_FROM not configured. Configure in .env or GitHub Secrets")
    if not EMAIL_PASSWORD:
        raise ValueError("EMAIL_PASSWORD not configured. Configure in .env or GitHub Secrets")
    if not EMAIL_TO:
        raise ValueError("EMAIL_TO not configured. Configure in .env or GitHub Secrets")
    
    # Prepare email subject
    if subject is None:
        date_str = datetime.now().strftime("%m/%d/%Y")
        subject = f"Balancer Tokenomics Dataset Update - {date_str}"
    
    # Load email HTML template
    print("\n🎨 Loading email template...")
    try:
        html_body = load_email_template()
        print("   ✅ Template loaded successfully")
    except Exception as e:
        raise ValueError(f"Error loading email template: {e}")
    
    print(f"\n📋 Settings:")
    print(f"   From: {EMAIL_FROM}")
    print(f"   To: {EMAIL_TO}")
    print(f"   Subject: {subject}")
    print(f"   SMTP Server: {SMTP_SERVER}:{SMTP_PORT}")
    print(f"   Format: HTML")
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg['Subject'] = subject
    
    # Add email body (HTML)
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    
    # Attach CSV file only if it exists
    if csv_file.exists():
        print(f"\n📎 Attaching file: {csv_file.name}")
        try:
            with open(csv_file, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {csv_file.name}'
            )
            msg.attach(part)
            print(f"   ✅ CSV file attached")
        except Exception as e:
            print(f"   ⚠️  Error attaching CSV: {e}")
    else:
        print(f"\n⚠️  CSV file not found: {csv_file.name}")
        print(f"   Email will be sent without CSV attachment")
    
    # Send email
    print(f"\n📤 Sending email...")
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_FROM, EMAIL_TO, text)
        server.quit()
        
        print(f"✅ Email sent successfully!")
        print(f"   Recipient: {EMAIL_TO}")
        
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        raise


def main():
    """Main function"""
    try:
        send_email_with_csv()
        print("\n" + "=" * 60)
        print("✅ Process completed successfully!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Error during sending: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
