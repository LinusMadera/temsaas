import os
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from string import Template

import jwt
from config import (
    BASE_URL,
    COMPANY_NAME,
    EMAIL_FROM,
    JWT_ALGORITHM,
    JWT_SECRET,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_SERVER,
    SMTP_USERNAME,
    SOFTWARE_NAME,
)


def send_verification_email(to_email: str, token: str):
    subject = f"Verify your email for {SOFTWARE_NAME}"
    verification_link = (
        f"{BASE_URL}/auth/users/email/verify?token={token}"  # TODO: change to frontend url when frontend is ready
    )

    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, "..", "templates", "email_verification_template.html")
    with open(template_path, "r") as file:
        template = Template(file.read())

    html_content = template.safe_substitute(
        software_name=SOFTWARE_NAME,
        company_name=COMPANY_NAME,
        verification_link=verification_link,
        current_year=datetime.now().year,
    )

    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def create_verification_token(email: str):
    expiration = datetime.utcnow() + timedelta(hours=24)
    payload = {"email": email, "exp": expiration}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_email_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload["email"]
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def create_password_reset_token(email: str):
    expiration = datetime.utcnow() + timedelta(hours=1)
    payload = {"email": email, "exp": expiration, "type": "password_reset"}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_password_reset_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "password_reset":
            return None
        return payload["email"]
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def send_password_reset_email(to_email: str, token: str):
    subject = f"{SOFTWARE_NAME} | Password Reset"
    reset_link = f"{BASE_URL}/pass/password/reset?token={token}"  # TODO: change to frontend url when frontend is ready

    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, "..", "templates", "password_reset_template.html")
    with open(template_path, "r") as file:
        template = Template(file.read())

    html_content = template.safe_substitute(
        software_name=SOFTWARE_NAME, company_name=COMPANY_NAME, reset_link=reset_link, current_year=datetime.now().year
    )

    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
