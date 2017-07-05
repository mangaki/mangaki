from django.core.management.base import BaseCommand
from django.db.models import Count
from mangaki.utils.anidb import client
from mangaki.models import Artist, Role, Staff, Work, WorkTitle, ArtistSpelling, Language
from urllib.parse import parse_qs, urlparse


def get_or_create_artist(name):
    try:
        return Artist.objects.get(name=name)
    except Artist.DoesNotExist:
        pass
    try:
        return ArtistSpelling.objects.select_related('artist').get(was=name).artist
    except ArtistSpelling.DoesNotExist:
        pass
    # FIXME consider trigram search to find similar artists in Artist, ArtistSpelling
    true_name = input('I don\'t now %s (yet). Link to another artist? Type their name: ' % name)
    artist, _ = Artist.objects.get_or_create(name=true_name)
    ArtistSpelling(was=name, artist=artist).save()
    return artist


class Command(BaseCommand):
    args = ''
    help = 'Retrieve AniDB data'

    def add_arguments(self, parser):
        parser.add_argument('id', nargs='*', type=int)

    def handle(self, *args, **options):

        category = 'anime'
        start = 0
        if options.get('id'):
            anime_id = options.get('id')[0]
            anime = Work.objects.filter(category__slug='anime').get(id=anime_id)
            if anime.anidb_aid == 0:
                for reference in anime.reference_set.all():
                    if reference.url.startswith('http://anidb.net') or reference.url.startswith('https://anidb.net'):
                        query = urlparse(reference.url).query
                        anidb_aid = parse_qs(query).get('aid')
                        if anidb_aid:
                            anime.anidb_aid = anidb_aid[0]
                            anime.save()
            todo = Work.objects.filter(category__slug='anime', id=anime_id, anidb_aid__gt=0)
        else:
            todo = Work.objects\
                .only('pk', 'title', 'ext_poster', 'nsfw')\
                .annotate(rating_count=Count('rating'))\
                .filter(category__slug=category, rating_count__gte=6)\
                .exclude(anidb_aid=0)\
                .order_by('-rating_count')

        a = client
        i = 0

        for anime in todo:
            i += 1
            if i < start:
                continue
            print(i, ':', anime.title, anime.id)

            creators = a.get(anime.anidb_aid).creators
            worktitles = a.get(anime.anidb_aid).worktitles

            for worktitle in worktitles:
                language = Language.objects.get(iso639=worktitle[2])
                WorkTitle.objects.get_or_create(work=anime, title=worktitle[0], language=language, type=worktitle[1])
            retrieve_tags = anime.retrieve_tags(a)
            deleted_tags = retrieve_tags["deleted_tags"]
            added_tags = retrieve_tags["added_tags"]
            updated_tags = retrieve_tags["updated_tags"]
            kept_tags = retrieve_tags["kept_tags"]

            print(anime.title+":")
            if deleted_tags:
                print("\n\tLes tags enlevés sont :")
                for tag, tag_infos in deleted_tags.items():
                    print('\t\t[AniDB Tag ID #{}] {}: {} '.format(tag_infos["anidb_tag_id"], tag, tag_infos["weight"]))

            if added_tags:
                print("\n\tLes tags totalement nouveaux sont :")
                for tag, tag_infos in added_tags.items():
                    print('\t\t[AniDB Tag ID #{}] {}: {} '.format(tag_infos["anidb_tag_id"], tag, tag_infos["weight"]))

            if updated_tags:
                print("\n\tLes tags modifiés sont :")
                for tag, tag_infos in updated_tags.items():
                    print('\t\t[AniDB Tag ID #{} -> #{}] {}: {} -> {}'.format(
                        tag_infos[0]["anidb_tag_id"], tag_infos[1]["anidb_tag_id"], tag, tag_infos[0]["weight"], tag_infos[1]["weight"]))


            if kept_tags:
                print("\n\tLes tags non modifiés/restés identiques sont :")
                for tag, tag_infos in kept_tags.items():
                    print('\t\t[AniDB Tag ID #{}] {}: {} '.format(tag_infos["anidb_tag_id"], tag, tag_infos["weight"]))

            choice = input("Voulez-vous réaliser ces changements [y/n] : ")
            if choice == 'n':
                print("\nOk, aucun changement ne va être fait")
            elif choice == 'y':
                anime.update_tags(deleted_tags, added_tags, updated_tags)

            staff_map = dict(Role.objects.filter(slug__in=['author', 'director', 'composer']).values_list('slug', 'pk'))

            for creator in creators.findAll('name'):
                artist = get_or_create_artist(creator.string)
                if creator['type'] == 'Direction':
                    staff_id = 'director'
                elif creator['type'] == 'Music':
                    staff_id = 'composer'
                elif creator['type'] == 'Original Work' or creator['type'] == 'Story Composition':
                    staff_id = 'author'
                else:
                    staff_id = None
                if staff_id is not None:
                    Staff.objects.get_or_create(work=anime, role_id=staff_map[staff_id], artist=artist)
                anime.save()
