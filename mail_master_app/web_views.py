from django.shortcuts import render
# Create your views here.
from django.shortcuts import redirect
from google_auth_oauthlib.flow import InstalledAppFlow
import requests
from  urllib.parse import urlencode
from rest_framework.decorators import api_view
from mail_master_app.models import Credentials
from rest_framework import  status 
from rest_framework.response import Response
from MailMaster.settings import FRONTEND_URL
from mail_master_app.google_api import Retrieve_deatails, Retrieve_history_deatails, get_user_email, mail_send_using_google_api
from mail_master_app.utils import ACTIVE


def authorize(request, credentials_id):
    context = {"msg":""}
    credentials = Credentials.objects.filter(id=credentials_id).first()
    if credentials:
        try:
            client_secret_file_path = credentials.api_credentials_file.path
            redirect_uri = credentials.api_credentials_text['redirect_uris'][0]
        except:
            context['msg'] = "Athentication Failed Please Add Google Api Credentials json file for Gmail Authentication"
            return render(request,'redirect_error.html', context)
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secret_file_path,
            scopes=['https://mail.google.com/','https://www.googleapis.com/auth/drive.metadata.readonly','https://www.googleapis.com/auth/postmaster.readonly'],
            redirect_uri= redirect_uri
        )
        authorization_url, state = flow.authorization_url(prompt='consent',access_type='offline',include_granted_scopes='true')
        request.session['credentials_id'] = str(credentials_id)
        return redirect(authorization_url)
    context['msg'] = "Credentials Does Not Exist"
    return render(request,'redirect_error.html', context)


def oauth2callback(request):
    code = request.GET.get('code')
    credentials_id = request.session.get('credentials_id')
    context = {"msg":""}
    if credentials_id:
        credentials = Credentials.objects.filter(id=credentials_id).first()
        if credentials :
            redirect_uri = credentials.api_credentials_text['redirect_uris'][0]
            client_id = credentials.api_credentials_text['client_id']
            client_secret = credentials.api_credentials_text['client_secret']
            token_uri = credentials.api_credentials_text['token_uri']
            params = {
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri
            }
            token_uri = token_uri + "?" + urlencode(params)
            response = requests.post(token_uri)
            if response.status_code == 200:
                credentials.credentials_text = response.json()
                credentials.status = ACTIVE
                credentials.save()
                context['msg'] = "Successfully logged in"
                context['domain'] = FRONTEND_URL
                return render(request,'redirect_home.html', context)
            context['domain'] = FRONTEND_URL
            context['msg'] = f"Invalid credentials returned error: {response.text}, Please try again"
            return render(request,'redirect_error.html', context)
        context['domain'] = FRONTEND_URL
        context['msg'] = "Credentials Object Not Found, Please try again"
        return render(request,'redirect_error.html', context)
    context['domain'] = FRONTEND_URL
    context['msg'] = "Credentials id not in Session, Please try again"
    return render(request,'redirect_error.html', context)

@api_view(['POST'])
def refresh(request):
    credential_id = request.data.get('credential_id')
    credentials = Credentials.objects.filter(id=credential_id).first()
    refresh_token = credentials.credentials_text['refresh_token']
    client_id = credentials.api_credentials_text['client_id']
    client_secret = credentials.api_credentials_text['client_secret']
    token_uri = credentials.api_credentials_text['token_uri']
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    response = requests.post(token_uri, data=params)
    if response.status_code == 200:
        data = response.json()
        access_token = data.get('access_token')
        credentials.credentials_text['access_token'] = access_token
        credentials.save()
        return Response(response.json() ,status=status.HTTP_200_OK) # *importent - not came refresh token this responce
    return Response(response.json() , status=status.HTTP_200_OK)


@api_view(['POST'])
def send_test_email(request):
    credential_id = request.data.get('credential_id')
    msg_id = request.data.get('msg_id')
    historyId = request.data.get('historyId')
    
    credentials = Credentials.objects.filter(id=credential_id).first()
    access_token = credentials.credentials_text['access_token']
    status = None
    msg = None
    to = None
    if not msg_id:
        msg, status, msg_id, to = send_email(access_token)
    details = Retrieve_deatails(access_token,msg_id)
    history = None
    if historyId:
        history = Retrieve_history_deatails(access_token,historyId)
    responce = {
                "status": status,
                "message_id": msg_id,
                "msg": msg,
                "recipient": to,
                "deatails": details,
                "history" : history
            }
    return Response(responce)


def send_email(access_token):
    from googleapiclient.errors import HttpError
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    import base64
    to = "muhammedrahilmadathingal@gmail.com"
    if to:
        message = MIMEMultipart()
        subject = "Apply Now"
        message['to'] = str(to)
        message['subject'] = subject   
        from_user = get_user_email(access_token)       
        message['from'] = f"LALU <{from_user}>"
        message.attach(MIMEText("Get Starts Now", 'plain'))
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        message = {"raw": raw_message}
        try:
            msg_id = mail_send_using_google_api(access_token, message, url_based = False)
            return 'Success', 200 , msg_id, to
        except HttpError as error:
            return str(error), 400, None, to
    return "Recipient Not Found", 404, None, None



from google.oauth2.credentials import Credentials as GoogleCredentials
from googleapiclient.discovery import build

@api_view(['POST'])
def post_master(request, credential_id):
    credential = Credentials.objects.filter(id=credential_id).first()
    
    if credential:
        access_token = credential.credentials_text['access_token']
        credentials = GoogleCredentials(access_token)
        service = build('gmailpostmastertools', 'v1beta1', credentials=credentials)
        domains = service.domains().list().execute()
        if not domains:
            print('No domains found.')
            return Response({'msg': 'No domains found.'}, status=status.HTTP_400_BAD_REQUEST)  
        else:
            print('Domains:')
            domainsList = []
            for domain in domains['domains']:
                domainsList.append(domain)
            return Response({'msg': 'Domains',"data": domainsList}, status=status.HTTP_200_OK)
        # your_domain = 'zaiportal.com'
        # url = f'https://gmailpostmastertools.googleapis.com/v1/domains/'
        # headers = {'Authorization': f'Bearer {access_token}'}
        # response = requests.get(url, headers=headers)
        # return Response({'msg': response.json()}, status=status.HTTP_200_OK)
    return Response({'msg': 'Credentials Do not exist'}, status=status.HTTP_400_BAD_REQUEST)
