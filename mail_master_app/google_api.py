from google.oauth2.credentials import Credentials as GoogleCredentials
from googleapiclient.discovery import build
import requests



def mail_send_using_google_api(access_token, message, url_based = False):
    if url_based:
        sent_message =  requests.post(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/send?access_token={access_token}",json=message
            )
        sent_message = sent_message.json() # if successful 200 status code
    else:
        credentials = GoogleCredentials(access_token)
        service = build('gmail', 'v1', credentials=credentials)
        sent_message = service.users().messages().send(userId='me', body=message).execute()
    msg_id = sent_message.get('id')
    return msg_id


# Retrieve the details of the specific email message using its id
def Retrieve_deatails(access_token,message_id):
    try:
        credentials = GoogleCredentials(access_token)
        service = build('gmail', 'v1', credentials=credentials)
        message = service.users().messages().get(userId='me', id=message_id).execute()
        return message
    except Exception as e:
        print("Failed to retrieve message:", str(e))


def Retrieve_history_deatails(access_token,history_id):
    try:
        credentials = GoogleCredentials(access_token)
        service = build('gmail', 'v1', credentials=credentials)
        history = service.users().history().list(userId='me', startHistoryId=history_id).execute()
        return history
    except Exception as e:
        print("Failed to retrieve history:", str(e))


# Retrieve the list of sent messages
def list_sent_messages(access_token):
    try:
        credentials = GoogleCredentials(access_token)
        service = build('gmail', 'v1', credentials=credentials)
        sent_messages = service.users().messages().list(userId='me', labelIds=['SENT']).execute()        
        messages = sent_messages.get('messages', [])
        return messages
    except Exception as e:
        print("Failed to retrieve sent messages:", str(e))
        return None

def get_user_email(access_token):
    try:
        credentials = GoogleCredentials(access_token)
        service = build('gmail', 'v1', credentials=credentials)
        profile = service.users().getProfile(userId='me').execute()
        email_address = profile.get('emailAddress')
        return email_address
    except Exception as e:
        return None
    