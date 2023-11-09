from rest_framework import serializers
from mail_master_app.models import *
from mail_master_app.utils import get_member_id, get_member_name, get_platform_id, get_project_id, get_memberplatform_id
import chardet
from MailMaster import settings
import json
from mail_master_app.models import Credentials


class CredentialsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Credentials
        fields = '__all__'
        
    def create(self, validated_data):
        validated_data['created_by'] = get_member_id(self.context.get('request'))
        validated_data['created_by_name'] = get_member_name(self.context.get('request'))
        validated_data['user_id'] = get_member_id(self.context.get('request'))
        validated_data['memberplatform_id'] = get_memberplatform_id(self.context.get('request'))
        validated_data['platform_id'] = get_platform_id(self.context.get('request'))
        validated_data['project_id'] = get_project_id(self.context.get('request'))
        
        api_credentials_file = validated_data.get('api_credentials_file')
        # this is json file dictionary data structure add api_credentials_text model field
        if api_credentials_file:
            api_credentials_file = api_credentials_file.read()
            file_encoding = chardet.detect(api_credentials_file)['encoding']
            api_credentials_file = api_credentials_file.decode(file_encoding)
            api_credentials_json = json.loads(api_credentials_file)
            web_credentials = api_credentials_json.get('web')
            if web_credentials:
                validated_data['api_credentials_text'] = web_credentials
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data['updated_by'] = get_member_id(self.context.get('request'))
        validated_data['updated_by_name'] = get_member_name(self.context.get('request'))
        api_credentials_file = validated_data.get('api_credentials_file')
        validated_data['redirect_uri'] = False
        if api_credentials_file:
            api_credentials_file = api_credentials_file.read()
            file_encoding = chardet.detect(api_credentials_file)['encoding']
            api_credentials_file = api_credentials_file.decode(file_encoding)
            api_credentials_json = json.loads(api_credentials_file)
            web_credentials = api_credentials_json.get('web')
            if web_credentials:
                validated_data['api_credentials_text'] = web_credentials
            validated_data['status'] = INACTIVE
            validated_data['redirect_uri'] = True
        return super().update(instance, validated_data)
    
    def to_representation(self, instance):
        single_representation = super().to_representation(instance)
        if instance.image:
            single_representation['image'] = f"{settings.MY_DOMAIN}{instance.image.url}"
        current_status = "inactive"
        if instance.status == 1:
            current_status = "active"
        single_representation["current_status"] = current_status
        single_representation["file_name"] = None
        if instance.api_credentials_file:
            single_representation["file_name"] = str(instance.api_credentials_file.url).replace('/media/credentials/api_credentials_file/','')
        return single_representation
    

class MailDeatailSerializer(serializers.ModelSerializer):
    class Meta:
        model = MailDeatail
        fields = '__all__'
    
    def validate(self, attrs):
        recipient_sheets = attrs.get('recipient_sheets')
        credential = attrs.get('credential')
        subject = attrs.get('subject')
        if not credential:
            raise serializers.ValidationError({"msg": "The credential is required"})
        if credential and credential.status != ACTIVE:
            raise serializers.ValidationError({"msg": "This credential Not Authenticated, So Not getting access token, please authenticate and try again"})
        if not recipient_sheets:
            raise serializers.ValidationError({"msg": "The Recipient sheets is required"})
        if not subject:
            raise serializers.ValidationError({"msg": "The Subject is required"})
        return super().validate(attrs)
    
    
    def to_representation(self, instance):
        single_representation =super().to_representation(instance)
        attachments = instance.attachments.all()
        all_attachments = []
        for attachment in attachments:
            all_attachments.append({
                "id" : attachment.id,
                "attachment_file" : f"{settings.MY_DOMAIN}{attachment.attachments.url}"
            })
        single_representation["attachments"] = all_attachments
        return single_representation
    
    def create(self, validated_data):
        validated_data['created_by'] = get_member_id(self.context.get('request'))
        validated_data['created_by_name'] = get_member_name(self.context.get('request'))
        validated_data['user_id'] = get_member_id(self.context.get('request'))
        validated_data['memberplatform_id'] = get_memberplatform_id(self.context.get('request'))
        validated_data['platform_id'] = get_platform_id(self.context.get('request'))
        validated_data['project_id'] = get_project_id(self.context.get('request'))
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data['updated_by'] = get_member_id(self.context.get('request'))
        validated_data['updated_by_name'] = get_member_name(self.context.get('request'))
        return super().update(instance, validated_data)
    

class TrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tracking
        fields = '__all__'
    
    def create(self, validated_data):
        validated_data['created_by'] = get_member_id(self.context.get('request'))
        validated_data['user_id'] = get_member_id(self.context.get('request'))
        validated_data['memberplatform_id'] = get_memberplatform_id(self.context.get('request'))
        validated_data['platform_id'] = get_platform_id(self.context.get('request'))
        validated_data['project_id'] = get_project_id(self.context.get('request'))
        return super().create(validated_data)
    
    

class TemplatesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Templates
        fields = '__all__'

    def create(self, validated_data):
        validated_data['created_by'] = get_member_id(self.context.get('request'))
        validated_data['created_by_name'] = get_member_name(self.context.get('request'))
        validated_data['user_id'] = get_member_id(self.context.get('request'))
        validated_data['memberplatform_id'] = get_memberplatform_id(self.context.get('request'))
        validated_data['platform_id'] = get_platform_id(self.context.get('request'))
        validated_data['project_id'] = get_project_id(self.context.get('request'))
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        validated_data['updated_by'] = get_member_id(self.context.get('request'))
        validated_data['updated_by_name'] = get_member_name(self.context.get('request'))
        return super().update(instance, validated_data)