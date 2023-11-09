import random
import pandas as pd
import io
import chardet
import requests
from email.mime.application import MIMEApplication
import pdfkit
import os
from MailMaster import settings
import datetime
import imgkit
from django.template.loader import render_to_string


INACTIVE = 0
ACTIVE = 1
DRAFT = 2
DELETE = 3

def get_member_id(request):
    try:
        if request.auth:
            return request.auth['user_id']
    except:
        pass
    return None


def get_member_name(request):
    try:
        if request.auth:
            name = f"{request.auth['first_name']} {request.auth['last_name']}"
            return name
    except:
        pass
    return None


def get_platform_id(request):
    try:
        if request.auth:
            return request.auth['platform_id']
    except:
        pass
    return None


def get_project_id(request):
    try:
        if request.auth:
            return request.auth['project_id']
    except:
        pass
    return None


def get_usertype(request):
    try:
        if request.auth:
            return request.auth['usertype']
    except:
        pass
    return None


def get_memberplatform_id(request):
    try:
        if request.auth:
            return request.auth['memberplatform_id']
    except:
        pass
    return None


def import_sheets(sheet, orient="records",unique_values=[]):
    try:
        import_sheet = sheet.read()
        file_encoding = chardet.detect(import_sheet)['encoding']
        import_sheet = import_sheet.decode(file_encoding)
        df = pd.read_csv(io.StringIO(import_sheet))
        df.columns = df.columns.str.replace('\n', '')
        df.columns = map(str.lower, df.columns)
        df.columns = map(str.strip, df.columns)
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        df = df.fillna('')
        cleaned_data = df.drop_duplicates(keep='first')
        if len(unique_values) > 0:
            for unique in unique_values:
                if unique in df.columns:
                    cleaned_data = cleaned_data.drop_duplicates(subset=[unique], keep="first")
        cleaned_data_dict = cleaned_data.to_dict(orient=orient)
    except:
        df = pd.read_excel(sheet)
        df.columns = df.columns.str.replace('\n', '')
        df.columns = map(str.lower, df.columns)
        df.columns = map(str.strip, df.columns)
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        df = df.fillna('')
        cleaned_data = df.drop_duplicates(keep='first')
        # if len(unique_values) > 0:
        #     for unique in unique_values:
        #         if unique in df.columns:
        #             cleaned_data = cleaned_data.duplicated(subset=[unique], keep="first")
        cleaned_data_dict = cleaned_data.to_dict(orient=orient)
    return cleaned_data_dict, df


def url_attachment(message,file_url):
    response = requests.get(file_url)
    if response.status_code == 200:
        file_content = response.content
        file_name = file_url.split("/")[-1]  # Extract the file name from the URL
        part = MIMEApplication(file_content, Name=file_name)
        part['Content-Disposition'] = f'attachment; filename="{file_name}"'
        message.attach(part)
        return message
    return message


def file_attachment(message,file_path):
    with open(file_path, 'rb') as file:
        part = MIMEApplication(file.read(), Name=file_path.split('/')[-1])
        part['Content-Disposition'] = f'attachment; filename="{file_path.split("/")[-1]}"'
        message.attach(part)
    return message


def get_email_html_content_template_name(email_html_content):
    emailHtml_path = None
    if len(email_html_content) != 0:
        email_html_content_template_name = f'email_html{random.randint(1,1000000000000)}.html'
        emailHtml_path = os.path.join("templates/", email_html_content_template_name) 
        with open(emailHtml_path, 'w', encoding='utf-8') as html_file:
            html_file.write(email_html_content)
    return emailHtml_path

# convertion part

def get_convertion_html_template(html_content):
    convetion_html_path = None
    if html_content:
        convetion_html_file_name = f"convetion_html_file_name{random.randint(1,1000000000000)}.html"
        convetion_html_path = os.path.join("templates/", convetion_html_file_name)
        with open(convetion_html_path, 'w', encoding='utf-8') as html_file:
            html_file.write(html_content)
    return convetion_html_path


def html_page_to_convertion_content(convertion_type, convetion_html_path, file_name, string = False, convertion_context={}, is_path_delete=False):
    if convetion_html_path:
        pdfkit_file_url = None
        if convertion_type == "PDF":
            pdfkit_file_url, pdf_file_name = html_to_pdf(convetion_html_path, file_name, string, convertion_context=convertion_context)
        if convertion_type == "JPG":
            pdfkit_file_url, pdf_file_name = html_to_jpg(convetion_html_path, file_name, string, convertion_context=convertion_context)
        if convertion_type == "JPEG":
            pdfkit_file_url, pdf_file_name = html_to_jpeg(convetion_html_path, file_name, string, convertion_context=convertion_context)
        if is_path_delete:
            delete_file_in_directory(convetion_html_path)
        return pdfkit_file_url, pdf_file_name
    return None


def convertion_filename_and_filepath(file_name, UPLOAD_FOLDER, convertion_type):
    pdfkit_filename = f'{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.{convertion_type}'
    if file_name:
        pdfkit_filename = f'{file_name}{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.{convertion_type}'
    output_file_path = f'{UPLOAD_FOLDER}/{pdfkit_filename}'
    return output_file_path, pdfkit_filename


def convertion(convetion_html_path, output_file_path, string : bool, is_pdfkit=True, convertion_context = {}):
    options = {
        'page-size': 'Letter',
        'encoding': "UTF-8",
        'no-outline': None
    }
    if string:
        convetion_html_path = os.path.basename(convetion_html_path)
        convetion_html_path = render_to_string(template_name= convetion_html_path, context=convertion_context)
    windows = False
    if is_pdfkit:
        pdfkit_convertion(convetion_html_path, output_file_path, options, string, windows)
    else:
        imgkit_convertion(convetion_html_path, output_file_path, options, string, windows)
    return


def pdfkit_convertion(convetion_html_path, output_file_path, options, string: bool, windows: bool):
    if not string:
        if windows:
            path_wkhtmltopdf = 'C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe'  # Replace with your actual path
            config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
            try:
                pdfkit.from_file(convetion_html_path, output_file_path, configuration=config, options=options)
            except:
                pass
        else:
            try:
                pdfkit.from_file(convetion_html_path, output_file_path, options=options)
            except Exception as e:
                print("" , str(e))
    else:
        if windows:
            path_wkhtmltopdf = 'C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe'  # Replace with your actual path
            config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
            try:
                pdfkit.from_string(convetion_html_path, output_file_path, configuration=config, options=options)
            except:
                pass
        else:
            try:
                pdfkit.from_string(convetion_html_path, output_file_path, options=options)
            except Exception as e:
                print("" , str(e))
    return


def imgkit_convertion(convetion_html_path, output_file_path, options, string: bool, windows: bool):
    if not string:
        if windows:
            path_wkhtmltopdf = 'C:/Program Files/wkhtmltopdf/bin/wkhtmltoimage.exe'  # Replace with your actual path
            config = imgkit.config(wkhtmltoimage = path_wkhtmltopdf, xvfb='/opt/bin/xvfb-run')
            try:
                imgkit.from_file(convetion_html_path, output_file_path, config=config)
            except:
                pass
        else:
            try:
                imgkit.from_file(convetion_html_path, output_file_path)
            except Exception as e:
                print("" , str(e))
    else:
        if windows:
            path_wkhtmltopdf = 'C:/Program Files/wkhtmltopdf/bin/wkhtmltoimage.exe'  # Replace with your actual path
            config = imgkit.config(wkhtmltoimage = path_wkhtmltopdf, xvfb='/opt/bin/xvfb-run')
            try:
                imgkit.from_string(convetion_html_path, output_file_path, config=config)
            except:
                pass
        else:
            try:
                imgkit.from_string(convetion_html_path, output_file_path)
            except Exception as e:
                print("" , str(e))
    return


def html_to_pdf(convetion_html_path, file_name, string :bool, convertion_context = {}):
    UPLOAD_FOLDER = "media/html_to_pdf/"
    if not os.path.exists(UPLOAD_FOLDER):
        os.mkdir(UPLOAD_FOLDER)
    output_file_path, pdfkit_filename = convertion_filename_and_filepath(file_name, UPLOAD_FOLDER, "pdf")
    convertion(convetion_html_path, output_file_path, string, is_pdfkit=True, convertion_context=convertion_context)
    pdfkit_file_url = f"{settings.MY_DOMAIN}/{UPLOAD_FOLDER}{pdfkit_filename}"
    return pdfkit_file_url, f"{UPLOAD_FOLDER}{pdfkit_filename}"


def html_to_jpg(convetion_html_path, file_name, string :bool, convertion_context= {}):
    UPLOAD_FOLDER = "media/html_to_jpg/"
    if not os.path.exists(UPLOAD_FOLDER):
        os.mkdir(UPLOAD_FOLDER)
    output_file_path, pdfkit_filename = convertion_filename_and_filepath(file_name, UPLOAD_FOLDER, "jpg")
    convertion(convetion_html_path, output_file_path, string, is_pdfkit=False, convertion_context=convertion_context)
    pdfkit_file_url = f"{settings.MY_DOMAIN}/{UPLOAD_FOLDER}{pdfkit_filename}"
    return pdfkit_file_url, f"{UPLOAD_FOLDER}{pdfkit_filename}"


def html_to_jpeg(convetion_html_path, file_name, string :bool, convertion_context={}):
    UPLOAD_FOLDER = "media/html_to_jpeg/"
    if not os.path.exists(UPLOAD_FOLDER):
        os.mkdir(UPLOAD_FOLDER)
    output_file_path, pdfkit_filename = convertion_filename_and_filepath(file_name, UPLOAD_FOLDER, "jpeg") 
    convertion(convetion_html_path, output_file_path, string, is_pdfkit=False, convertion_context=convertion_context)
    pdfkit_file_url = f"{settings.MY_DOMAIN}/{UPLOAD_FOLDER}{pdfkit_filename}"
    return pdfkit_file_url, f"{UPLOAD_FOLDER}{pdfkit_filename}"

## end convertion part


def chunked(iterable, chunk_size):
    """Generator to yield chunks of items from an iterable."""
    for i in range(0, len(iterable), chunk_size):
        yield iterable[i:i + chunk_size]
        
        
        
def create_recipient_sample_sheet(headers=[]):
    date_frames = pd.DataFrame(columns=headers)
    csv_name = 'recipients-sample-sheet'
    UPLOAD_FOLDER = "media/"
    if not os.path.exists(UPLOAD_FOLDER): 
        os.mkdir(UPLOAD_FOLDER)
    date_frames.to_csv(f'{UPLOAD_FOLDER}{csv_name}.csv', index=False)
    return f'{settings.MY_DOMAIN}/{UPLOAD_FOLDER}{csv_name}.csv'.replace(
            '//media', '/media'), f"{csv_name}.csv"
    
    
def delete_file_in_directory(file_name):
    try:
        if file_name:
            if os.path.exists(file_name):
                os.remove(file_name)
    except Exception as e:
        print(f"file delete error - file name {file_name}  error - {str(e)}")
    return