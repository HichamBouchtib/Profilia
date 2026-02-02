import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os

def send_email(to_email: str, subject: str, body: str, attachment_data: bytes = None, attachment_filename: str = None) -> bool:
    """Send an email using SMTP settings from environment variables.

    Returns True on success, False otherwise. Failures are logged but non-fatal.
    """
    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = os.environ.get('SMTP_PORT')
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')
    smtp_from = os.environ.get('SMTP_FROM', smtp_user or 'noreply@example.com')
    use_tls = os.environ.get('SMTP_USE_TLS', 'true').lower() in ('1', 'true', 'yes')

    if not smtp_host or not smtp_port:
        print(f"❌ SMTP not configured: SMTP_HOST={smtp_host}, SMTP_PORT={smtp_port}", flush=True)
        logging.warning('SMTP not configured; skipping email send')
        return False
    
    # Debug: Print SMTP configuration (without password)
    print(f"🔧 SMTP Config: Host={smtp_host}, Port={smtp_port}, User={smtp_user}, TLS={use_tls}", flush=True)

    try:
        # Use MIMEMultipart if we have an attachment, otherwise use simple EmailMessage
        if attachment_data and attachment_filename:
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = smtp_from
            msg['To'] = to_email
            
            # Add body text
            msg.attach(MIMEText(body, 'plain'))
            
            # Add PDF attachment
            pdf_attachment = MIMEApplication(attachment_data, _subtype='pdf')
            pdf_attachment.add_header('Content-Disposition', 'attachment', filename=attachment_filename)
            msg.attach(pdf_attachment)
        else:
            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = smtp_from
            msg['To'] = to_email
            msg.set_content(body)

        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
            if use_tls:
                server.starttls(context=context)
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            
            if attachment_data and attachment_filename:
                server.send_message(msg)
            else:
                server.send_message(msg)
                
        print(f"✅ Email sent successfully to {to_email}{' with attachment' if attachment_data else ''}", flush=True)
        logging.info('Email sent to %s%s', to_email, ' with attachment' if attachment_data else '')
        return True
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {str(e)}", flush=True)
        logging.error('Failed to send email to %s: %s', to_email, e)
        return False
