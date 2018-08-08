from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from mangaki.tasks import MALImporter, import_mal
from mangaki.utils.mal import client


class MALImportRateThrottle(UserRateThrottle):
    scope = 'mal_import'


class MALImportUnavailable(APIException):
    status_code = 503
    default_detail = 'MAL import temporarily unavailable, try again later.'
    default_code = 'mal_import_unavailable'


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
@throttle_classes([MALImportRateThrottle])
def import_from_mal(request: Request, mal_username: str) -> Response:
    if client.is_available:
        importer = MALImporter()
        pending_import = importer.get_current_import_for(request.user)
        if not pending_import:
            result = import_mal.s(mal_username, request.user.username).apply_async()
            task_id = result.task_id
        else:
            task_id = pending_import.task_id

        return Response({
            'task_id': task_id,
            'message': 'Already importing' if pending_import else 'Import is starting'
        })
    else:
        raise MALImportUnavailable()
