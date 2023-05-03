import smtplib
import ssl
import os
from email.message import EmailMessage
from typing import List

class MissingGmailLogin(Exception):
    """Gmail info Missing. Expecting key in env var GMAIL_API_KEY and email address in GMAIL_ACCOUNT."""
    pass

class EmailClient():
    def __init__(self):
        try:
            self.apikey = os.environ["GMAIL_API_KEY"]
            self.sender = os.environ["GMAIL_ACCOUNT"]
        except KeyError:
            raise MissingGmailLogin
            
        # Create a secure SSL context
        port = 465  # For SSL
        context = ssl.create_default_context()
        self.server = smtplib.SMTP_SSL("smtp.gmail.com", port, context=context)
        self.server.login(self.sender, self.apikey)

    def send_email(self, subject: str, to: List[str], content: str):
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = self.sender
        msg['To'] = to 
        msg.set_content(content)

        self.server.send_message(msg)

    def quit_server(self):
        self.server.quit()
    