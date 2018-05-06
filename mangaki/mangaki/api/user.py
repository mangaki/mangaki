import csv
import io
from django.http import HttpResponse

from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from zipfile import ZipFile

from mangaki.models import Profile, Rating, Suggestion


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


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def export_user_data(request: Request):
    """
    Export user data in CSV format.
    """
    user = request.user

    # FIXME: implement caching and do not recompute an archive everytime.
    # FIXME: we should do this on-disk.
    # FIXME: we should stream the response?
    # 1. Ratings data
    ratings_csv_buffer = io.StringIO()
    ratings_writer = csv.writer(ratings_csv_buffer)
    ratings_writer.writerow(['title', 'date', 'choice'])
    for rating in Rating.objects.filter(user=user).prefetch_related('work__title').iterator():
        ratings_writer.writerow(
            [rating.work.title, rating.date, rating.choice]
        )

    # 2. Suggestion data
    suggestion_csv_buffer = io.StringIO()
    suggestion_writer = csv.writer(suggestion_csv_buffer)
    suggestion_writer.writerow(['title', 'date', 'problem', 'message', 'is_checked'])
    for suggestion in Suggestion.objects.filter(user=user).prefetch_related('work__title').iterator():
        suggestion_writer.writerow(
            [suggestion.work.title,
             suggestion.date,
             suggestion.problem,
             suggestion.message,
             suggestion.is_checked]
        )

    # 3. Combine and create the ZIP archive
    zip_archive_buffer = io.BytesIO()
    files = [('ratings.csv', ratings_csv_buffer), ('suggestions.csv', suggestion_csv_buffer)]
    with ZipFile(zip_archive_buffer, 'w') as zp_file:
        for filename, io_buffer in files:
            zp_file.writestr(filename, io_buffer.getvalue())

    response = HttpResponse(
        zip_archive_buffer.getvalue(),
        content_type='application/zip'
    )

    response['Content-Disposition'] = 'inline; filename=user_archive.zip'

    return response
