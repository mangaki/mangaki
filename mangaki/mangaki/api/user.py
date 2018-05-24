from datetime import datetime

import django.db
from django.core.files import File

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from sendfile import sendfile

from mangaki.models import Profile, UserArchive
from mangaki.utils.archive_export import export, UserDataArchiveBuilder


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


@api_view(['DELETE'])
@permission_classes((IsAuthenticated,))
def delete_user_profile(request: Request):
    """
    Delete the profile and its underlying user from the database.
    """
    request.user.delete()
    return Response()


# Every day.
USER_EXPORT_DATA_CACHE_PERIOD = 24*3600


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def export_user_data(request: Request):
    """
    Export all user data in a zip blob and serve it through sendfile.
    """
    user = request.user

    # Cleanup old archives.
    cache_expiration = datetime.fromtimestamp(datetime.now().timestamp() - USER_EXPORT_DATA_CACHE_PERIOD)
    for archive in UserArchive.objects.filter(owner=user,
                                              updated_on__lte=cache_expiration).iterator():
        try:
            archive.local_archive.delete()
        except ValueError:
            pass
        finally:
            archive.delete()

    try:
        archive = UserArchive.objects.get(owner=user)
        return sendfile(request, archive.local_archive.path)
    except (UserArchive.DoesNotExist, OSError, IOError, ValueError):
        try:
            builder = UserDataArchiveBuilder(user)
            export(builder)
            archive, _ = UserArchive.objects.get_or_create(owner=user)
            builder.archive.close()  # save the ZIP file.
            archive.local_archive.save('data.zip',
                                       File(open(builder.archive_filename, 'rb')))
            builder.cleanup()
            return sendfile(request, archive.local_archive.path)
        except (OSError, IOError, django.db.Error) as e:
            print(e)
            return Response({}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
