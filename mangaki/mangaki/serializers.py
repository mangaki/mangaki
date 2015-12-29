from rest_framework import serializers
from mangaki import models

WORK_FIELDS = ('id',
               'title',
               'source',
               'poster',
               'nsfw',
               'date',
               'synopsis')

class AnimeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Anime
        fields = WORK_FIELDS + ('director',
                  'composer',
                  'studio',
                  'editor',
                  'anime_type',
                  'genre',
                  'nb_episodes',
                  'origin',
                  'anidb_aid')

class MangaSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Manga
        fields = WORK_FIELDS + ('vo_title',
                  'mangaka',
                  'writer',
                  'editor',
                  'origin',
                  'genre',
                  'manga_type')

class EditorSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Editor
        fields = ('id', 'title')

class StudioSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Studio
        fields = ('id', 'title')

class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Genre
        fields = ('id', 'title')

class TrackSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Track
        fields = ('id', 'title', 'ost')

class OSTSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.OST
        fields = WORK_FIELDS

class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Artist
        fields = ('id',
                  'first_name',
                  'last_name')

class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Rating
        fields = ('id',
                  'user',
                  'work',
                  'choice')

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Profile
        fields = ('id',
                  'user',
                  'is_shared',
                  'nsfw_ok',
                  'newsletter_ok',
                  'reco_willsee_ok',
                  'avatar_url',
                  'mal_username',
                  'score')

class SuggestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Suggestion
        fields = ('id',
                  'user',
                  'work',
                  'date',
                  'problem',
                  'message',
                  'is_checked')

