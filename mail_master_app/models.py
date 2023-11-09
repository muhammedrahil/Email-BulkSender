from django.db import models
import uuid
from mail_master_app.utils import ACTIVE, INACTIVE

from mail_master_app.validator import validate_json_extension, validate_recipient_extension, validate_image_pdf_extension, validate_image_extension



class Credentials(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False)
    user_id = models.UUIDField(blank=True,null=True)
    memberplatform_id = models.UUIDField(blank=True,null=True)
    platform_id = models.UUIDField(blank=True,null=True)
    project_id = models.UUIDField(blank=True,null=True)
    first_name = models.CharField(max_length=256,null=True,blank=True)
    last_name = models.CharField(max_length=256,null=True,blank=True)
    email = models.EmailField(max_length=128, null=True, blank=True)
    api_credentials_file = models.FileField(null=True,validators=[validate_json_extension],upload_to='credentials/api_credentials_file/')
    api_credentials_text = models.JSONField(default=dict, null=True)
    credentials_file = models.FileField(null=True,upload_to='credentials/credentials_file/')
    credentials_text = models.JSONField(default=dict, null=True)
    image = models.ImageField(null=True,upload_to='credentials/image/',validators=[validate_image_extension])
    status = models.PositiveIntegerField(default=INACTIVE)
    created_by = models.UUIDField(null=True)
    created_by_name = models.CharField(max_length=256,null=True,blank=True)
    updated_by = models.UUIDField(null=True)
    updated_by_name = models.CharField(max_length=256,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

CONVERTIONS = (
    ('PDF','HTML TO PDF'),
    ('JPG','HTML TO JPG'),
    ('JPEG','HTML TO JPEG'),
)
    
class MailDeatail(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False)
    user_id = models.UUIDField(blank=True,null=True)
    memberplatform_id = models.UUIDField(blank=True,null=True)
    platform_id = models.UUIDField(blank=True,null=True)
    project_id = models.UUIDField(blank=True,null=True)
    from_alias = models.CharField(max_length=256,null=True,blank=True) #
    credential = models.ForeignKey(Credentials,null=True,related_name="api_credential",on_delete=models.SET_NULL)
    subject = models.CharField(max_length=256,null=True,blank=True)
    description = models.TextField(null=True,blank=True)
    html_page_text = models.TextField(null=True,blank=True)
    html_page_to_pdf_content = models.TextField(null=True,blank=True)
    html_convertion_type = models.CharField(max_length=256, choices=CONVERTIONS,null=True,blank=True, default=CONVERTIONS[0][0])
    html_variables = models.JSONField(null=True, blank=True)
    convertions_variables = models.JSONField(null=True, blank=True)
    other_variables = models.JSONField(null=True, blank=True)
    attachments = models.ManyToManyField('MailAttachment', blank=True,related_name="mail_deatail_attachments",)
    recipient_sheets = models.FileField(null=True,validators=[validate_recipient_extension],upload_to='mail_deatails/recipient_sheets/')
    delay = models.IntegerField(default=0,null=True)
    status = models.PositiveIntegerField(default=ACTIVE)
    send_counts = models.IntegerField(default=50,null=True)
    recipients_count = models.PositiveIntegerField(default=0)
    created_by = models.UUIDField(null=True)
    created_by_name = models.CharField(max_length=256,null=True,blank=True)
    updated_by = models.UUIDField(null=True)
    updated_by_name = models.CharField(max_length=256,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class MailAttachment(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False)
    attachments = models.FileField(null=True,validators=[validate_image_pdf_extension],upload_to='mail_deatails/attachments/')
    created_by = models.UUIDField(null=True)
    updated_by = models.UUIDField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

        
class Tracking(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False)
    user_id = models.UUIDField(blank=True,null=True)
    memberplatform_id = models.UUIDField(blank=True,null=True)
    platform_id = models.UUIDField(blank=True,null=True)
    project_id = models.UUIDField(blank=True,null=True)
    mail_deatail = models.OneToOneField(MailDeatail,on_delete=models.SET_NULL,null=True,related_name="mail_deatail")
    recipient_list = models.JSONField(null=True, blank=True)
    recipients_count = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    success_list = models.JSONField(null=True, blank=True)
    failure_count = models.PositiveIntegerField(default=0)
    failure_list = models.JSONField(null=True, blank=True)
    tacking_deatails = models.JSONField(null=True, blank=True)
    created_by = models.UUIDField(null=True)
    updated_by = models.UUIDField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Templates(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False)
    user_id = models.UUIDField(blank=True,null=True)
    memberplatform_id = models.UUIDField(blank=True,null=True)
    platform_id = models.UUIDField(blank=True,null=True)
    project_id = models.UUIDField(blank=True,null=True)
    name = models.CharField(max_length=256,null=True,blank=True)
    description = models.TextField(null=True, blank=True)
    html_page_text = models.TextField(null=True,blank=True)
    status = models.PositiveIntegerField(default=ACTIVE)
    created_by = models.UUIDField(null=True)
    created_by_name = models.CharField(max_length=256,null=True,blank=True)
    updated_by = models.UUIDField(null=True)
    updated_by_name = models.CharField(max_length=256,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)