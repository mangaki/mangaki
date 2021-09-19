from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from mangaki.tasks import AniListImporter, import_anilist
from mangaki.wrappers.anilist import AniList
from mangaki.api.importation.base import ImportMechanismUnavailable


class AniListImportRateThrottle(UserRateThrottle):
    scope = 'anilist_import'


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
@throttle_classes([AniListImportRateThrottle])
def import_from_anilist(request: Request, anilist_username: str) -> Response:
    client = AniList()
    if client.is_available:
        importer = AniListImporter()
        pending_import = importer.get_current_import_for(request.user)
        if not pending_import:
            result = import_anilist.s(request.user.username, anilist_username).apply_async()
            task_id = result.task_id
        else:
            task_id = pending_import.task_id

        return Response({
            'task_id': task_id,
            'message': 'Already importing' if pending_import else 'Import is starting'
        })
    else:
        raise ImportMechanismUnavailable

