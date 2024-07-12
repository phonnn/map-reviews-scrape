import os
import uuid
from flask_mail import Mail, Message


def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


def generate_id():
    return str(uuid.uuid4())


def send_email_with_attachment(mail: Mail, recipient: str, subject: str, body: str, attachment_path: str):
    """
    Sends an email with an attachment using Flask-Mail.

    Args:
    - mail (Mail): Flask-Mail instance.
    - recipient (str): Email recipient.
    - subject (str): Email subject.
    - body (str): Email body text.
    - attachment_path (str): Path to the file to attach.
    """
    msg = Message(subject, sender=mail.default_sender, recipients=[recipient])
    msg.body = body

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, 'rb') as attachment:
            msg.attach(os.path.basename(attachment_path), "application/octet-stream", attachment.read())  # Adjust MIME type as needed


    mail.send(msg)
