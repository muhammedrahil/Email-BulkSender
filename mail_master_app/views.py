import os
from MailMaster import settings
from mail_master_app.google_api import get_user_email, mail_send_using_google_api
from mail_master_app.models import *
from mail_master_app.pagination import CustomPagination, StandardResultSetPagination
from mail_master_app.serializer import CredentialsSerializer, MailDeatailSerializer, TemplatesSerializer, TrackingSerializer
from rest_framework.response import Response
from rest_framework import viewsets, status , filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.decorators import action
from mail_master_app.task import  celery_worker_run
from mail_master_app.utils import ACTIVE, DELETE, get_convertion_html_template, create_recipient_sample_sheet, get_email_html_content_template_name, get_member_id, get_usertype, html_page_to_convertion_content, import_sheets, url_attachment, get_memberplatform_id
import datetime
from googleapiclient.errors import HttpError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from mail_master_app.models import Credentials
from rest_framework.permissions import IsAuthenticated
import requests
import base64
import concurrent.futures
from django.db.models import Sum

class CredentialsViewSet(viewsets.ModelViewSet):
    serializer_class = CredentialsSerializer
    pagination_class = StandardResultSetPagination
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    permission_classes = (IsAuthenticated,)
    search_fields = ['first_name','last_name','email']

    def get_queryset(self):
        memberplatform_id = get_memberplatform_id(self.request)
        queryset = Credentials.objects.exclude(status=DELETE).order_by('-created_at')
        if get_usertype(self.request) != "Administrator":
            queryset = queryset.filter(memberplatform_id=memberplatform_id)
        return queryset
    
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except:
            return Response({"msg": "Credentials Not found."}, status=status.HTTP_404_NOT_FOUND)
        setattr(instance, 'status', DELETE)
        instance.save()
        return Response({'msg': 'Credentials Deleted Successfully'}, status=status.HTTP_200_OK)
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)  
        user_id = get_member_id(request)
        senders_count = Credentials.objects.filter(status__in=[ACTIVE,INACTIVE])
        if get_usertype(self.request) != "Administrator":
            senders_count = senders_count.filter(user_id=user_id)
        senders_count = senders_count.count()
        dispatched_email_count = MailDeatail.objects.filter(status=ACTIVE)
        if get_usertype(self.request) != "Administrator":
            dispatched_email_count = dispatched_email_count.filter(user_id=user_id)
        dispatched_email_count = dispatched_email_count.aggregate(recipients_count=Sum('recipients_count')) or 0
        dispatched_email_count = dispatched_email_count.get('recipients_count', 0)
        response.data['senders_count'] = senders_count
        response.data['dispatched_email_count'] = dispatched_email_count
        response.data['users_count'] = users_count(request) or 0 
        return response
    
    
def users_count(request):
    count = 0
    if get_usertype(request) == "Administrator":
        member_list_url = f"{settings.USERMANAGEMENT_URL}/members/list/"
        headers = {'Authorization': f'Bearer {request.auth}',}
        responce = requests.get(url=member_list_url, headers=headers)
        if responce.status_code == 200:
            responce = responce.json()
            count = responce.get('total',0)
    return count
    
    
class MailDetailViewSet(viewsets.ModelViewSet):
    serializer_class = MailDeatailSerializer
    pagination_class = StandardResultSetPagination
    permission_classes = (IsAuthenticated,)
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['subject','description','created_by_name']

    def get_queryset(self):
        memberplatform_id = get_memberplatform_id(self.request)   
        queryset = MailDeatail.objects.exclude(status__in=[INACTIVE,DELETE]).order_by('-created_at')
        if get_usertype(self.request) != "Administrator":
            queryset = queryset.filter(memberplatform_id=memberplatform_id)
        return queryset

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except:
            return Response({"msg": "Despatch Not found."}, status=status.HTTP_404_NOT_FOUND)
        setattr(instance, 'status', DELETE)
        instance.save()
        return Response({'msg': 'Despatch Deleted Successfully'}, status=status.HTTP_200_OK)

    # @action(detail=False, methods=['delete'])
    # def delete_all(self, request):
    #     # deleted_count, _ ===> count , {'App.Model': count} eg:{'mail_master_app.Credentials': 1}
    #     deleted_count, _ = MailDeatail.objects.all().delete()
    #     return Response({"message": f"Deleted {deleted_count} items"}, status=status.HTTP_204_NO_CONTENT)
    
    
    def create(self, request, *args, **kwargs):
        single_create_data = super(MailDetailViewSet, self).create(request, *args, **kwargs).data
        instance  = MailDeatail.objects.get(id=single_create_data['id'])
        instance = add_attachments(request, instance)
        recipient_sheet_name = request.data.get('recipient_sheets').name if request.data.get('recipient_sheets') else ""
        recipient_sheets = instance.recipient_sheets
        cleaned_datas, df = import_sheets(recipient_sheets, unique_values=['email'])        
        if df.empty:
            return Response({"msg": f"The '{recipient_sheet_name}' file is empty or contains only empty rows and columns."}, status=status.HTTP_400_BAD_REQUEST)
        msg, status_code = send_bulk_emails(instance=instance, cleaned_datas=cleaned_datas, delay=instance.delay, send_counts=instance.send_counts)
        if status_code == 400:
            return Response({"msg": msg },status=status.HTTP_400_BAD_REQUEST)
        return Response({"msg": "Email Send Successfully","data":single_create_data},status=status.HTTP_200_OK)


def add_attachments(request, instance):
    files = request.FILES
    other_variables = instance.other_variables or {}
    intial_attachment_count = 0
    attachment_suffix = other_variables.get('attachment_suffix')
    attachment_random = other_variables.get('attachment_start_number') or 0
    for key,file in files.items():
        if key != 'recipient_sheets':
            if attachment_suffix:
                random_number = int(attachment_random) + intial_attachment_count
                _, file_extension = os.path.splitext(file.name)
                new_file_name = f"{attachment_suffix}{random_number}{file_extension}"
                intial_attachment_count += 1
                file.name = new_file_name
            attachment = MailAttachment.objects.create(attachments=file,created_by=get_member_id(request))
            instance.attachments.add(attachment)
    return instance


def send_bulk_emails(instance=None, cleaned_datas={}, delay=0, send_counts=0):
    try:
        credential = instance.credential
        if is_token_expired(credential):
            credential, status_code = get_access_token_by_using_refresh_token(credential)
            if status_code == 400:
                print("Access token note received")
                return str(credential), 400
        access_token = credential.credentials_text.get('access_token')
            
        if len(cleaned_datas) > 0:
            email_subject = instance.subject or ""
            emailMsg = instance.description or ""
            convertion_type = instance.html_convertion_type
            email_html_content= instance.html_page_text or ""
            html_variables = instance.html_variables or {}
            convertions_variables = instance.convertions_variables or {}
            other_variables = instance.other_variables or {}
            
            # Convertions section
            convetion_html_content = instance.html_page_to_pdf_content
            convetion_html_path = get_convertion_html_template(convetion_html_content)
            convertion_url = None
            pdf_file_name = None
            if convertion_type != 'PDF':
                convertion_url, pdf_file_name = html_page_to_convertion_content(convertion_type, convetion_html_path, other_variables.get('file_name'), is_path_delete =True)
            
            instance.recipients_count = len(cleaned_datas)
            instance.save()
            traking_id = Tracking.objects.create(
                user_id=instance.user_id,
                project_id=instance.project_id,
                platform_id=instance.platform_id,
                memberplatform_id=instance.memberplatform_id,
                mail_deatail=instance,
                recipient_list=cleaned_datas,
                recipients_count=len(cleaned_datas),
                success_list = [],
                failure_list = [],
                tacking_deatails = {}
                ).id
            
            attachment_urls_list = []
            instance_attachments = instance.attachments.all()
            for attachment in instance_attachments:
                attachment_url = attachment.attachments.url
                attachment_url = f"{settings.MY_DOMAIN}{attachment_url}"
                attachment_urls_list.append(attachment_url)

            html_suffix_start_number = html_variables.get('start_number') or 0
            convertion_suffix_start_number = convertions_variables.get('start_number') or 0
            html_sufix = html_variables.get('suffix') or ""
            convetion_sufix = convertions_variables.get('suffix') or ""
            
            # add random number variables in sheet
            for index, cleaned_data in enumerate(cleaned_datas,0):
                if len(html_sufix) != 0:
                    html_prefix = int(html_suffix_start_number or 0) + index
                    cleaned_data['html_suffix_start_number'] = f'{html_sufix}{html_prefix}'
                    
                if len(convetion_sufix) != 0:
                    convertion_prefix = int(convertion_suffix_start_number or 0) + index
                    cleaned_data['convertion_suffix_start_number'] = f'{convetion_sufix}{convertion_prefix}'
            
            # add string content write a html to page name
            emailHtml_path = get_email_html_content_template_name(email_html_content)
                    
            from_alias = None
            if instance.from_alias:
                from_email = get_user_email(access_token)
                if from_email:
                    from_alias = f"{instance.from_alias} <{from_email}>"
                    
            context = {
                "instance_id" : str(instance.id),
                "traking_id": str(traking_id),
                "email_subject": email_subject,
                "emailMsg": emailMsg,
                "from_alias": from_alias,
                "convertion_type": convertion_type,
                "attachment_urls_list": attachment_urls_list,
                "convertion_html_path": convetion_html_path,
                "emailHtml_path": emailHtml_path,
                "html_variables" : html_variables,
                "convertions_variables" : convertions_variables,
                "other_variables" : other_variables,
                "convertion_url": convertion_url,
                "pdf_file_name": pdf_file_name
            }
            celery_worker_run.delay(access_token, context=context, cleaned_datas=cleaned_datas, delay=delay, send_counts=send_counts)
            
            # is_celery_worker = True
            # is_thread_pool_worker = False
            # recipient_chunks = list(chunked(cleaned_datas, send_counts))
            # for recipients in recipient_chunks:
            #     if is_celery_worker:
            #         msg_code = celery_worker(single_create, access_token, recipients, attachment_url_list, mail_traking_id)
            #     if is_thread_pool_worker:
            #         msg_code = thread_pool_worker(single_create, access_token, recipients, attachment_url_list)
            #     time.sleep(delay)
            
            return "Successfully Sended", 200
        return 'recipients Not found' , 400
    except Exception as e:
        return str(e), 400


def is_token_expired(auth_credential):
    token_expiry = auth_credential.credentials_text.get('expires_in')
    expiry_datetime = datetime.datetime.utcfromtimestamp(int(token_expiry))
    current_datetime = datetime.datetime.utcnow()
    if current_datetime >= expiry_datetime:
        return True
    return False


def get_access_token_by_using_refresh_token(auth_credential):
    refresh_token = auth_credential.credentials_text.get('refresh_token')
    client_id = auth_credential.api_credentials_text.get('client_id')
    client_secret = auth_credential.api_credentials_text.get('client_secret')
    token_uri = auth_credential.api_credentials_text.get('token_uri')
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
        expires_in = data.get('expires_in')
        auth_credential.credentials_text['access_token'] = access_token
        auth_credential.credentials_text['expires_in'] = expires_in
        auth_credential.save()
        return auth_credential , 200
    return response.text, 400


# thread pool worker

def thread_pool_worker(single_create, access_token, recipients, attachment_url_list):
    num_threads = 5
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_to_email = {executor.submit(send_email,single_create, recipient, access_token, attachment_url_list): recipient for recipient in recipients}
        for future in concurrent.futures.as_completed(future_to_email):
            email = future_to_email[future]
            try:
                future.result()  # Wait for the email sending task to complete
                print(f"Email sent to: {email}")
            except Exception as e:
                print(f"Error sending email to {email}: {e}")
    return 200



def send_email(single_create, recipient, access_token, attachment_url_list):
    to = recipient.get('email')
    if to:
        message = MIMEMultipart()
        for attachment_url in attachment_url_list:
            url_attachment(message,attachment_url)
        html_page_to_pdf_url = single_create.html_page_to_pdf_url
        url_attachment(message,html_page_to_pdf_url)
        
        subject = single_create.subject
        emailMsg= single_create.description
        emailHtml= single_create.html_page_text
        message['to'] = str(recipient)
        message['subject'] = subject
        # message.replace_header('To', str(recipient))
        # message.replace_header('Subject', subject)
                
        message.attach(MIMEText(emailMsg, 'plain'))
        message.attach(MIMEText(emailHtml, 'html'))
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        message = {"raw": raw_message}
        try:
            sent_message = mail_send_using_google_api(access_token, message, url_based = False)
            return 'Success', 200
        except HttpError as error:
            return str(error), 400
    return "Not Found", 404

# thread pool worker



class MailDeatailTrackingAPIView(APIView):
    
    def get(self, request, maildeatail_id, format=None):
        tracking = Tracking.objects.filter(mail_deatail_id=maildeatail_id).first()
        serializer_data = TrackingSerializer(tracking).data
        return Response(serializer_data)
    


class TrackingViewSet(viewsets.ModelViewSet):
    queryset = Tracking.objects.all()
    pagination_class = StandardResultSetPagination
    serializer_class = TrackingSerializer
    
    # @action: This decorator indicates that you're defining a custom action for the ViewSet
    # detail=False: This argument specifies that the action does not operate on a single instance (detail), but on the entire collection. In other words, it's a bulk operation that affects all instances.
    # methods=['delete']: This specifies that the custom action should only respond to HTTP DELETE requests.
    # @action(detail=False, methods=['delete'])
    # def delete_all(self, request):
    #     # deleted_count, _ ===> count , {'App.Model': count} eg:{'mail_master_app.Credentials': 1}
    #     deleted_count, _ = Tracking.objects.all().delete()
    #     return Response({"message": f"Deleted {deleted_count} items"}, status=status.HTTP_204_NO_CONTENT)
    
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def credentials_dropdown(request):
    search = request.GET.get('search')
    memberplatform_id = get_memberplatform_id(request)
    queryset = Credentials.objects.filter(status=ACTIVE).order_by('-created_at')
    if get_usertype(request) != "Administrator":
        queryset = queryset.filter(memberplatform_id=memberplatform_id)
    if search:
        queryset = queryset.filter(email__icontains=search)
    queryset = queryset.values('id',"email")
    return Response(queryset, status=status.HTTP_200_OK)



@api_view(['DELETE'])
def delete_all(request):
    Credentials.objects.all().delete()
    MailDeatail.objects.all().delete()
    MailAttachment.objects.all().delete()
    Tracking.objects.all().delete()
    Templates.objects.all().delete()
    return Response("All delete successfully", status=status.HTTP_200_OK)


class DispatchEmailsDateFilterAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = MailDeatailSerializer
    pagination_class = CustomPagination().get_pagination
    
    
    def get(self, request):
        date_time = request.GET.get('date_time')
        queryset = MailDeatail.objects.exclude(status__in=[INACTIVE,DELETE]).order_by('-created_at')
        if date_time :
            date_time = datetime.datetime.strptime(date_time, '%Y-%m-%d')
            memberplatform_id = get_memberplatform_id(request)   
            if get_usertype(request) != "Administrator":
                queryset = queryset.filter(memberplatform_id=memberplatform_id)
            queryset = queryset.filter(created_at__date = date_time)
        return self.pagination_class(self, request, queryset)
    

@api_view(['GET'])
def recipients_sheet(request):
    file_url, file_name = create_recipient_sample_sheet(headers = ['First Name','Last Name','Email'])
    context  = {
        "file_name": file_name,
        "file_url": file_url
    }
    return Response(context, status=status.HTTP_200_OK)


@api_view(['GET'])
def callbackurl(request):
    context  = {
        "callbackurl": f'{settings.MY_DOMAIN}/oauth2callback/'
    }
    return Response(context, status=status.HTTP_200_OK)

class TemplatesViewSet(viewsets.ModelViewSet):
    serializer_class = TemplatesSerializer
    pagination_class = StandardResultSetPagination
    permission_classes = (IsAuthenticated,)
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['name','description','created_by_name']
    
    def get_queryset(self):
        memberplatform_id = get_memberplatform_id(self.request)
        queryset = Templates.objects.exclude(status=DELETE).order_by('-created_at')
        if get_usertype(self.request) != "Administrator":
            queryset = queryset.filter(memberplatform_id=memberplatform_id)
        return queryset
    
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except:
            return Response({"msg": "Templates Not found."}, status=status.HTTP_404_NOT_FOUND)
        setattr(instance, 'status', DELETE)
        instance.save()
        return Response({'msg': 'Templates Deleted Successfully'}, status=status.HTTP_200_OK)
    
    def dropdown(self, request):
        queryset = self.get_queryset()
        queryset = queryset.values('id','name')
        return Response(queryset, status=status.HTTP_200_OK)
    
    
    
@api_view(['GET'])
def alias_name(request,credentials_id):
    credentials = Credentials.objects.filter(id= credentials_id).first()
    first_name = credentials.first_name or ""
    last_name = credentials.last_name or ""
    email_alias_name = f"{first_name} {last_name}".strip()
    return Response({"alias_name":email_alias_name}, status=status.HTTP_200_OK)