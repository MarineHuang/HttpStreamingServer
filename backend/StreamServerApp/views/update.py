from django.core.management.base import BaseCommand
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
import traceback
from django.core.cache import cache
from StreamServerApp.tasks import update_db_from_local_folder_async


class RestUpdate(APIView):
    def post(self, request):
        try:
            user = request.user
            #return self.get_history(request, user)
        except Exception as ex:
            traceback.print_exception(type(ex), ex, ex.__traceback__)
            return Response({}, status=status.HTTP_401_UNAUTHORIZED)

        keep_files = True
        try:
            print(request.data["headers"]["keep_files"])
            if ("false" == request.data["headers"]["keep_files"]):
                keep_files = False
        except Exception as ex:
            keep_files = True

        dryrun = False
        try:
            print(request.data["headers"]["dryrun"])
            if (request.data["headers"]["dryrun"]):
                dryrun = True
        except Exception as ex:
            dryrun = False

        is_updateing = cache.get("is_updating")
        if is_updateing is None or is_updateing == "false":
            is_updateing = cache.set("is_updating", "true", timeout=None)
            if not dryrun:
                update_db_from_local_folder_async.delay(keep_files)     
            return Response({}, status=status.HTTP_200_OK)
        else:
            return Response({}, status=status.HTTP_226_IM_USED)
