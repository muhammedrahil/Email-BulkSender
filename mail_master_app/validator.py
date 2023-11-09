import os
from django.core.exceptions import ValidationError


def validate_json_extension(value):
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.json']
    if ext.lower() not in valid_extensions:
        raise ValidationError(
            'Unsupported file extension. Only Json file allowed')
        
        
def validate_recipient_extension(value):
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.csv','.xlsx','.xls']
    if ext.lower() not in valid_extensions:
        raise ValidationError(
            'Unsupported file extension. Only Csv, Xlsx, Xls file allowed')
        
        
def validate_image_pdf_extension(value):
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.png', '.jpg', '.jpeg', '.pdf', '.ppt', '.doc', '.xls']
    if ext.lower() not in valid_extensions:
        raise ValidationError(
            'Unsupported file extension. Only PNG, JPG, JPEG, PDF, DOC, XLS, PPT file allowed')
        
        
def validate_image_extension(value):
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.png', '.jpg', '.jpeg']
    if ext.lower() not in valid_extensions:
        raise ValidationError(
            'Unsupported file extension. Only PNG, JPG, JPEG file allowed')