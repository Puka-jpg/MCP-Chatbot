import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()
mcp = FastMCP("email_appointment")

# Email configuration
GMAIL_EMAIL = os.getenv("GMAIL_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

EMAIL_TEMPLATE = """Dear {user},

Your appointment with NeuralFlow Technology is confirmed for {date}.

What to expect:
- Personalized AI strategy discussion
- Review of your business requirements  
- Timeline and implementation approach
- Q&A session with our experts

We'll contact you soon to confirm the exact time and provide meeting details.

Regards,
NeuralFlow Technology Team
AI & Machine Learning Solutions"""

@mcp.tool()
def send_email(receiver_email: str, user_name: str, appointment_date: str) -> str:
    """Send appointment confirmation email"""
    try:
        # Create email
        msg = MIMEMultipart()
        msg['From'] = GMAIL_EMAIL 
        msg['To'] = receiver_email
        msg['Subject'] = "Appointment Confirmation - NeuralFlow Technology"
        
        body = EMAIL_TEMPLATE.format(user=user_name, date=appointment_date)
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_EMAIL, receiver_email, msg.as_string())
        
        return f"Confirmation email sent successfully to {receiver_email}"
        
    except Exception as e:
        return "Failed to send confirmation email"

if __name__ == "__main__":
    print("Starting Email Server...")
    mcp.run(transport='stdio')