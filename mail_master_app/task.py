
import datetime
import os
import random
import time
from celery import shared_task
from googleapiclient.errors import HttpError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import base64
from mail_master_app.google_api import mail_send_using_google_api
from mail_master_app.models import *
from googleapiclient.errors import HttpError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import base64
import concurrent.futures
from django.template.loader import render_to_string
from mail_master_app.utils import chunked, delete_file_in_directory, html_page_to_convertion_content, url_attachment
import threading


thread_lock = threading.Lock()


@shared_task(bind=True)
def send_email_task(self, single_create_dict, recipient, access_token):
    to = recipient.get('email')
    if to:
        message = MIMEMultipart()
        attachment_url_list = single_create_dict.get('attachment_url_list')
        for attachment_url in attachment_url_list:
            url_attachment(message,attachment_url)
            
        html_page_to_pdf_url = single_create_dict.get('html_page_to_pdf_url')
        url_attachment(message,html_page_to_pdf_url)
        subject = single_create_dict.get('subject')
        emailMsg= single_create_dict.get('emailMsg')
        emailHtml= single_create_dict.get('emailHtml')
        message['to'] = str(recipient)
        message['subject'] = subject            
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



def celery_thread_pool_worker(context, access_token, recipients):
    num_threads = 5
    tracking = Tracking.objects.get(id=context.get('traking_id'))
    with concurrent.futures.ThreadPoolExecutor(max_workers = num_threads) as executor:
        future_to_email = {executor.submit(send_email_task_for_celery_thread_pool_worker, context, recipient, access_token): recipient for recipient in recipients}
        for future, recipient in future_to_email.items():
            msg, status, msg_id, to = future.result()
            responce = {
                "status": status,
                "message_id": msg_id,
                "msg": msg,
                "recipient": recipient
            }
            if status == 200:
                tracking.success_count += 1
                tracking.success_list.append(to)
            else:
                tracking.failure_count += 1
                tracking.failure_list.append(to)
            tracking.tacking_deatails.update({to : responce})
            tracking.save()
    return 200


def send_email_task_for_celery_thread_pool_worker(context, recipient, access_token):
    with thread_lock:
        to = recipient.get('email')
        if to:
            first_name = recipient.get('first name') or ""
            last_name = recipient.get('last name') or ""
            
            mime = MIMEMultipart()
            
            # attached attachments in a mimemultipart
            attachment_urls_list = context.get('attachment_urls_list')
            for attachment_url in attachment_urls_list:
                url_attachment(mime, attachment_url)
            
            # attached convert attachments part as well as pdf convertion and attached in a mimemultipart
            convertion_html_path = context.get('convertion_html_path')
            other_variables = context.get('other_variables')
            pdf_file_name = None
            if convertion_html_path:
                convertion_type = context.get('convertion_type')
                if convertion_type == "PDF":
                    convertion_context = context.get('convertions_variables')
                    file_name = other_variables.get('file_name')
                    if file_name:
                        file_name = f'{file_name}{random.randint(1,10000)}{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}'
                    convertions_suffix = convertion_context.get('suffix') or ""
                    if len(convertions_suffix) != 0:
                        convertion_context['random_number'] = recipient.get('convertion_suffix_start_number') or 0
                    convertion_context['first_name'] = first_name
                    convertion_context['last_name'] = last_name
                    convertion_url, pdf_file_name = html_page_to_convertion_content(convertion_type, convertion_html_path, file_name, string = True, convertion_context=convertion_context)
                    url_attachment(mime, convertion_url)
                else:
                    convertion_url = context.get('convertion_url')
                    if convertion_url:
                        url_attachment(mime, convertion_url)
            
            # html content section and add html content in email body
            emailHtml_path= context.get('emailHtml_path')
            email_html = ''
            if emailHtml_path:
                html_context = context.get('html_variables')
                html_content_suffix = html_context.get('suffix') or ""
                if len(html_content_suffix) != 0:
                    html_context['random_number'] = recipient.get('html_suffix_start_number')
                html_context['first_name'] = first_name
                html_context['last_name'] = last_name
                email_html_template_name = os.path.basename(emailHtml_path)
                email_html = render_to_string(template_name=email_html_template_name, context=html_context)

            # emailMsg= context.get('emailMsg') or f"Hi {first_name} {last_name}".strip()
            # mime.attach(MIMEText(emailMsg, 'plain'))

            email_subject = context.get('email_subject')
            from_alias = context.get('from_alias')
            if from_alias:
                mime['from'] = from_alias
            mime['to'] = str(to)
            mime['subject'] = email_subject           
            mime.attach(MIMEText(email_html, 'html'))
            
            # encode all body content
            raw_message = base64.urlsafe_b64encode(mime.as_bytes()).decode('utf-8')
            message = {"raw": raw_message}
            try:
                # send email
                msg_id = mail_send_using_google_api(access_token, message)
                delete_file_in_directory(pdf_file_name)
                return 'Success', 200 , msg_id, to
            except Exception as e:
                print(f"send email error - {str(e)}")
                delete_file_in_directory(pdf_file_name)
                return str(e), 400, None, to
        return "Recipient Not Found", 404, None, None


@shared_task(bind=True)
def celery_worker_run(self, access_token, 
                      context={}, cleaned_datas={}, delay=0, send_counts=0):
    recipient_chunks = list(chunked(cleaned_datas, send_counts))
    for recipients in recipient_chunks:
        celery_thread_pool_worker(context, access_token, recipients)
        time.sleep(delay)
        
    delete_file_in_directory(context.get('pdf_file_name'))
    delete_file_in_directory(context.get('emailHtml_path'))       
    delete_file_in_directory(context.get('convertion_html_path'))
    return 200