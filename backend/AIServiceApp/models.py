from django.db import models

# Create your models here.
class SpeechRecognizer(models.Model):
    name = models.CharField(max_length=200)
    producer = models.CharField(max_length=100)
    language = models.CharField(max_length=100)
    access_key_id = models.CharField(max_length=100)
    access_key_secret = models.CharField(max_length=100)
    app_key = models.CharField(max_length=200)
    oss_bucket_name = models.CharField(max_length=100)
    oss_endpoint_domain = models.CharField(max_length=100)
    oss_access_key_id = models.CharField(max_length=100)
    oss_access_key_secret = models.CharField(max_length=200)

    def __str__(self):
        return '{}'.format(self.name)