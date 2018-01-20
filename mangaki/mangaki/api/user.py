from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from mangaki.models import Profile


class UserProfileSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        exclude = ('id', 'user')


@api_view(['GET', 'PUT'])
@permission_classes((IsAuthenticated,))
def update_user_profile(request: Request):
    """
    Patch the profile settings of self or a given user when permitted.
    """
    if request.method == 'PUT':
        profile_serializer = UserProfileSettingsSerializer(request.user.profile,
                                                           data=request.data,
                                                           partial=True)

        profile_serializer.is_valid(raise_exception=True)
        profile = profile_serializer.save(user=request.user)
        return Response(UserProfileSettingsSerializer(profile).data)
    else:
        return Response(
            UserProfileSettingsSerializer(request.user.profile).data
        )
