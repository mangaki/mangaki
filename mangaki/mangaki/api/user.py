# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from datetime import datetime

import django.db
from django.contrib.auth.models import User
from django.db.models import Q
from django.core.files import File
from django.utils import timezone

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from sendfile import sendfile

from mangaki.models import Profile, UserArchive, Rating
from mangaki.utils.ratings import current_user_ratings, friend_ratings
from mangaki.utils.viz import get_2d_embeddings
from mangaki.utils.archive_export import export, UserDataArchiveBuilder
from mangaki.utils.values import rating_values
import pandas as pd
import numpy as np


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
    cache_expiration = datetime.fromtimestamp(timezone.now().timestamp() - USER_EXPORT_DATA_CACHE_PERIOD)
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
            return Response({}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['GET'])
@permission_classes((AllowAny,))
def get_user_and_friends_positions(request: Request, algo_name):
    """
    Compute the position of user and friends on the map
    """
    rated_works = current_user_ratings(request)
    df_mine = pd.DataFrame(rated_works.items(), columns=('work_id', 'choice'))
    df_mine['user_id'] = request.user.id if not request.user.is_anonymous else -1
    df_item_pos = pd.DataFrame(
        get_2d_embeddings(algo_name)['works']).set_index('work_id')
    available_works = df_item_pos.index

    if not request.user.is_anonymous:
        ratings = friend_ratings(request)
        df = pd.DataFrame(ratings, columns=('user_id', 'work_id', 'choice'))
        df_all = pd.concat((df_mine, df), axis=0)
    else:
        df_all = df_mine

    user_points = []
    user_ids = df_all['user_id'].unique().tolist()
    users = User.objects.in_bulk(user_ids)  # Get usernames for display
    df_all['rating'] = df_all['choice'].map(rating_values)
    for user_id in user_ids:
        this_user = df_all.query(
            'user_id == @user_id and choice == "favorite" and '
            'work_id in @available_works')
        if len(this_user):
            x, y = df_item_pos.loc[this_user['work_id'], ["x", "y"]].mean(axis=0)
            user_points.append({
                'title': f'{users[user_id].username}'
                         if user_id != -1 else 'yourself',
                'x': x, 'y': y})

    return Response(user_points)
