from django.urls import path
from django.conf.urls import url

from .views import RestTranscript

urlpatterns = [
    url(r'^transcript/', RestTranscript.as_view(), name='transcript'),  
]
