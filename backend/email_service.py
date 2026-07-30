import os
import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

EMAILS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "emails")

def save_email_locally(to_email, subject, html_content, email_type):
    # Ensure directory exists
    os.makedirs(EMAILS_DIR, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_email = to_email.replace("@", "_at_").replace(".", "_")
    filename = f"{email_type}_{safe_email}_{timestamp}.html"
    filepath = os.path.join(EMAILS_DIR, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"<!--\nTo: {to_email}\nSubject: {subject}\nDate: {datetime.datetime.now().isoformat()}\nType: {email_type}\n-->\n")
        f.write(html_content)
        
    try:
        print(f"\n[EMAIL LOGGER] Email saved to: {filepath}")
        print(f"[EMAIL LOGGER] Subject: {subject}")
    except Exception:
        # Fallback for Windows console encoding issue with emojis
        safe_subject = subject.encode('ascii', errors='replace').decode('ascii')
        print(f"\n[EMAIL LOGGER] Email saved to: {filepath}")
        print(f"[EMAIL LOGGER] Subject: {safe_subject}")
    print("-" * 50)
    return filepath

def send_email(to_email, subject, html_content, email_type="general"):
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = os.environ.get("SMTP_PORT")
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    smtp_from = os.environ.get("SMTP_FROM", "no-reply@habitflow.com")
    
    # Save a local copy always for debugging and testing purposes
    save_email_locally(to_email, subject, html_content, email_type)
    
    if not smtp_server or not smtp_user or not smtp_password:
        # If no credentials, we succeed gracefully with the logged local email file
        return True
        
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_from
        msg["To"] = to_email
        
        part = MIMEText(html_content, "html")
        msg.attach(part)
        
        port = int(smtp_port) if smtp_port else 587
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_from, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"[SMTP Error] Failed to send email via SMTP server: {e}")
        return False

def send_verification_email(to_email, name, code):
    subject = f"Verify your HabitFlow Account - Code: {code}"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e8e0; border-radius: 8px; background-color: #fcfdfc;">
        <h2 style="color: #2d5a27; border-bottom: 2px solid #2d5a27; padding-bottom: 10px;">Welcome to HabitFlow, {name}!</h2>
        <p>Thank you for signing up. Please verify your email address to activate your account.</p>
        <div style="background-color: #d8ebd4; padding: 15px; border-radius: 6px; text-align: center; margin: 20px 0;">
            <p style="font-size: 14px; margin: 0; color: #2d5a27;">Your Verification Code</p>
            <h1 style="font-size: 32px; letter-spacing: 5px; margin: 10px 0; color: #1c3818; font-weight: bold;">{code}</h1>
        </div>
        <p>Enter this verification code in the HabitFlow app to complete your registration. This code will expire in 24 hours.</p>
        <p style="color: #666; font-size: 12px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 10px;">
            If you did not register for HabitFlow, you can safely ignore this email.
        </p>
    </div>
    """
    return send_email(to_email, subject, html, "verification")

def send_reset_password_email(to_email, name, code):
    subject = f"Reset your HabitFlow Password - Code: {code}"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e8e0; border-radius: 8px; background-color: #fcfdfc;">
        <h2 style="color: #2d5a27; border-bottom: 2px solid #2d5a27; padding-bottom: 10px;">Reset Password Request</h2>
        <p>Hello {name},</p>
        <p>We received a request to reset your password for your HabitFlow account. Use the code below to complete the reset process:</p>
        <div style="background-color: #fdf5e6; border: 1px solid #ff9800; padding: 15px; border-radius: 6px; text-align: center; margin: 20px 0;">
            <p style="font-size: 14px; margin: 0; color: #ff9800;">Your Password Reset Code</p>
            <h1 style="font-size: 32px; letter-spacing: 5px; margin: 10px 0; color: #e65100; font-weight: bold;">{code}</h1>
        </div>
        <p>Enter this code on the reset page, along with your new password, to gain access back to your account.</p>
        <p style="color: #666; font-size: 12px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 10px;">
            If you did not request a password reset, you can safely ignore this email. Your password will remain unchanged.
        </p>
    </div>
    """
    return send_email(to_email, subject, html, "reset")

def send_weekly_report_email(to_email, name, report_html):
    subject = "Your HabitFlow Weekly Progress Report 🌿"
    # Wrap in standard styling
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e8e0; border-radius: 8px; background-color: #fcfdfc;">
        <div style="text-align: center; padding-bottom: 20px;">
            <span style="font-size: 40px;">🌿</span>
            <h2 style="color: #2d5a27; margin: 5px 0;">HabitFlow Weekly Report</h2>
            <p style="color: #666; margin: 0;">Keep growing your habits day by day</p>
        </div>
        
        <p>Hello {name},</p>
        <p>Here is your weekly summary of habit completions and consistency insights:</p>
        
        {report_html}
        
        <div style="text-align: center; margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px;">
            <p style="color: #666; font-size: 12px;">
                You are receiving this because weekly email updates are enabled on your HabitFlow profile settings.
            </p>
            <p style="color: #888; font-size: 11px;">
                HabitFlow Inc. &copy; 2026. Keep Flowing!
            </p>
        </div>
    </div>
    """
    return send_email(to_email, subject, html, "weekly_report")
