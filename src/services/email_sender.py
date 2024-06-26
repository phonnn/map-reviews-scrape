import os
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


class EmailSender:
    def __init__(self, smtp_server, smtp_port, sender_email, password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.password = password
        self.client = None

    async def connect(self):
        self.client = aiosmtplib.SMTP(hostname=self.smtp_server, port=self.smtp_port)
        await self.client.connect()
        # await self.client.starttls()
        await self.client.login(self.sender_email, self.password)

    async def send_email(self, recipient_email, subject, body, attachment_path=None):
        message = MIMEMultipart()
        message['From'] = self.sender_email
        message['To'] = recipient_email
        message['Subject'] = subject
        message.attach(MIMEText(body, 'html'))

        if attachment_path:
            with open(attachment_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(attachment_path)}')
                message.attach(part)

        await self.client.send_message(message)



# # sender_email = "k79pro@gmail.com"
# # password = "clol hprx vsxi nxxv"
# # recipient_email = "hungphongk97@gmail.com"
# # subject = "Hello from Python"
# # body = "with attachment"
#
# sender = EmailSender('smtp.gmail.com', 587, 'k79pro@gmail.com', 'clol hprx vsxi nxxv')
# sender.connect()
# file_path = f'../../temp/hungphongk97@gmail.com.csv'
# sender.send_email('hungphongk97@gmail.com', 'Test Subject', '<h1>Test Body</h1>', file_path)
