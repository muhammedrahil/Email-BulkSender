from django.urls import path, include
from rest_framework import routers

from .web_views import authorize, oauth2callback, post_master, refresh, send_test_email
from .views import *

router = routers.DefaultRouter()

router.register('credentials', CredentialsViewSet, basename='credentials_viewSet')
router.register('maildetails', MailDetailViewSet, basename='maildeatails_viewSet')
router.register('tracking', TrackingViewSet, basename='tracking_viewSet')
router.register('templates', TemplatesViewSet, basename='template_viewSet')



urlpatterns = [
    path('', include(router.urls)),
    
    # web routes for google authentication tokens
    path('authorize/<uuid:credentials_id>/', authorize, name='authorize'),
    path('oauth2callback/', oauth2callback, name='oauth2callback'),
    path('maildeatails/tracking/<uuid:maildeatail_id>/', MailDeatailTrackingAPIView.as_view(), name='maildeatail_tracking_api_view'),
    path('credential/dropdown/', credentials_dropdown, name='dropdown'),
    path('delete/all/', delete_all, name='delete_all'),
    path('dispatch/datefilter/', DispatchEmailsDateFilterAPIView.as_view(), name='dispatch_datefilter'),
    path('recipients/sheet/', recipients_sheet, name='recipients_sheet'),
    path('alias_name/<uuid:credentials_id>/', alias_name, name='alias_name'),
    path('template/dropdown/', TemplatesViewSet.as_view({"get": "dropdown"})),
    path('callbackurl/', callbackurl , name='callbackurl'),
    
    path('refresh/', refresh , name='refresh'),
    path('test_email/', send_test_email , name='test_email'),
    path('post_master/<uuid:credential_id>', post_master , name='post_master'),
    
]