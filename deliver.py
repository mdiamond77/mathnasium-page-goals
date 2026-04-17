"""
deliver.py
Email the output file and upload it to Google Drive.
"""

import json
import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from config import DRIVE_FOLDER_ID

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def send_email(
    filepath: str,
    month_name: str,
    recipients: list[str],
    smtp_user: str,
    smtp_password: str,
    error_message: str = None,
) -> None:
    """
    Send the output file as an email attachment.
    If error_message is provided, send an error notification instead.
    """
    filename = os.path.basename(filepath) if filepath else None

    if error_message:
        subject = f"⚠️ Page Goals Automation Failed — {month_name}"
        body = f"The {month_name} page goals automation failed with the following error:\n\n{error_message}"
        msg = MIMEText(body, "plain")
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = ", ".join(recipients)
    else:
        subject = f"{month_name} Page Goals"
        body = f"Please find attached the {month_name} page goals report."
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(body, "plain"))

        with open(filepath, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
        msg.attach(part)

    print(f"[deliver] Sending email to: {', '.join(recipients)}")
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, recipients, msg.as_string())
    print("[deliver] Email sent.")


def upload_to_drive(filepath: str, credentials_json: str) -> str:
    """
    Upload filepath to the configured Google Drive folder.
    credentials_json: the service account JSON as a string.
    Returns the webViewLink of the uploaded file.
    """
    creds_dict = json.loads(credentials_json)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/drive.file"],
    )
    service = build("drive", "v3", credentials=creds)

    filename = os.path.basename(filepath)
    file_metadata = {"name": filename, "parents": [DRIVE_FOLDER_ID]}
    media = MediaFileUpload(
        filepath,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    print(f"[deliver] Uploading {filename} to Google Drive...")
    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink",
    ).execute()

    link = uploaded.get("webViewLink", "")
    print(f"[deliver] Uploaded. Link: {link}")
    return link
