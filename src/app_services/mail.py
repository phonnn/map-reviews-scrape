# from flask import request, send_from_directory
# from flask_mail import Message
#
#
# def send_email_with_attachment(recipient):
#     # Render the HTML template
#     recipient_name = recipient.split('@')[0]  # Extract name from email for personalization
#     html_body = render_template('email_template.html', recipient_name=recipient_name)
#
#     # Attach a file (e.g., PDF)
#     with app.open_resource('path_to_your_attachment.pdf') as attachment:
#         msg = Message(subject='Hello from Flask-Mail with Attachment',
#                       sender='your-email@example.com',
#                       recipients=[recipient])
#         msg.html = html_body
#         msg.attach('attachment.pdf', 'application/pdf', attachment.read())
#
#         # Send email
#         mail.send(msg)
#
#     return 'Email with attachment sent successfully!'
