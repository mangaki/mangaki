from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from mangaki.models import UserBackgroundTask
from mangaki.tasks import convert_external_ratings


class ExternalRatingConversionRateThrottle(UserRateThrottle):
    scope = 'external_rating_conversion'


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
@throttle_classes([ExternalRatingConversionRateThrottle])
def convert_ratings(request: Request) -> Response:
    user = request.user
    pending_task_id = UserBackgroundTask.objects.filter(owner=user, tag='EXTERNAL_RATINGS').first()

    if pending_task_id:
        return Response({
            'task_id': pending_task_id,
            'message': 'Already converting'
        })
    else:
        result = convert_external_ratings.s(request.user.username).apply_async()
        return Response({
            'task_id': result.task_id,
            'message': 'Conversion has started'
        })
