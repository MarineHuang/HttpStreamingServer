from django.shortcuts import render

# Create your views here.
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from .transcription import transcript_media_file


class RestTranscript(APIView):
    def post(self, request):
        print("request to RestTranscript")
        #transcript_media_file(media_file_path="/usr/torrent/test.wav")
        return Response({}, status=status.HTTP_200_OK)