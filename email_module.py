from google.oauth2 import service_account
from googleapiclient.discovery import build

import os
import io
import base64
import time

# Path to your service account key file
SERVICE_ACCOUNT_FILE = 'docutrenchservicekey.json'

# Scopes for full Gmail access
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify'
    ]

def gmail_authenticate():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    # If accessing a user's Gmail in a Google Workspace domain, uncomment the next line
    credentials = credentials.with_subject('dan@docutrench.com')

    service = build('gmail', 'v1', credentials=credentials)
    return service

def get_email_details(service, user_id, message_id, store_dir, txt_dir):
    message = service.users().messages().get(userId=user_id, id=message_id, format='full').execute()

    # Extract headers for subject and recipient(s)
    headers = message['payload']['headers']
    subject = next(header['value'] for header in headers if header['name'] == 'Subject')
    to = next(header['value'] for header in headers if header['name'] == 'To')

    # Extract body
    body = ""
    if 'parts' in message['payload']:
        # Handle multipart email
        for part in message['payload']['parts']:
            if part['mimeType'] == 'text/plain':
                body += base64.urlsafe_b64decode(part['body']['data'].encode('UTF-8')).decode('utf-8')
            elif 'attachmentId' in part['body']:
                # Handle attachments
                file_data = get_attachment(service, user_id, message_id, part['body']['attachmentId'])
                filename = part.get('filename', 'attachment')
                path = os.path.join(store_dir, filename)
                with open(path, 'wb') as f:
                    f.write(file_data)
    else:
        # Handle non-multipart email
        body = base64.urlsafe_b64decode(message['payload']['body']['data'].encode('UTF-8')).decode('utf-8')

    # Save email details to a text file
    email_txt_filename = f"email_{message_id}.txt"
    with open(os.path.join(txt_dir, email_txt_filename), 'w', encoding='utf-8') as txt_file:
        txt_file.write(f"Subject: {subject}\n")
        txt_file.write(f"To: {to}\n")
        txt_file.write("Body:\n")
        txt_file.write(body)

    return {'subject': subject, 'to': to, 'body': body, 'txt_filename': email_txt_filename}

def get_attachment(service, user_id, message_id, attachment_id):
    attachment = service.users().messages().attachments().get(userId=user_id, messageId=message_id, id=attachment_id).execute()
    file_data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))
    return file_data

def delete_message(service, user_id, message_id):
    try:
        service.users().messages().delete(userId=user_id, id=message_id).execute()
        print(f"Deleted message {message_id}")
    except Exception as e:
        print(f"An error occurred: {e}")

def list_messages_and_process(service, user_id='dan@docutrench.com', store_dir='attachments', txt_dir='emails_txt'):
    # Ensure the directories exist
    os.makedirs(store_dir, exist_ok=True)
    os.makedirs(txt_dir, exist_ok=True)

    # Call the Gmail API to fetch messages
    results = service.users().messages().list(userId=user_id).execute()
    messages = results.get('messages', [])

    if not messages:
        print("No messages found.")
    else:
        for message in messages:
            msg_id = message['id']
            email_details = get_email_details(service, user_id, msg_id, store_dir, txt_dir)
            print(f"Email details saved to {email_details['txt_filename']}")
            delete_message(service, user_id, msg_id)
            print(f"Email deleted. Sleeping for a second")
            time.sleep(1)

    return messages



# Authenticate and process messages
service = gmail_authenticate()

while True: 
    list_messages_and_process(service)
    print("Module ran, sleeping!")
    time.sleep(5)
