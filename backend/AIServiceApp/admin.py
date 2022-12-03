from django.contrib import admin
from AIServiceApp.models import SpeechRecognizer

class SpeechRecognizerAdmin(admin.ModelAdmin):
    search_fields = ['name']
    model = SpeechRecognizer

# Register your models here.
admin.site.register(SpeechRecognizer, SpeechRecognizerAdmin)