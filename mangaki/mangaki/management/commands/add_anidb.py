from django.core.management.base import BaseCommand
from mangaki.utils.anidb import AniDB
from mangaki.models import Work, Category, Language, WorkTitle


def create_anime(**kwargs):
    anime = Category.objects.get(slug='anime')
    title = kwargs.pop('main_title')
    titles = kwargs.pop('titles')
    work = Work.objects.create(category=anime, title=title, **kwargs)
    languages = Language.objects.filter(lang_code__in=titles.keys()).all()
    lang_map = {
        lang.lang_code: lang for lang in languages
    }
    work_titles = []

    for lang, title_data in titles.items():
        lang_model = lang_map.get(lang)
        if lang_model:
            work_titles.append(
                WorkTitle(
                    work=work,
                    title=title_data['title'],
                    language=lang_model,
                    type=title_data['type']
                )
            )

    WorkTitle.objects.bulk_create(work_titles)
    return work

class Command(BaseCommand):
    args = ''
    help = 'Retrieve AniDB data'

    def add_arguments(self, parser):
        parser.add_argument('id', type=int)

    def handle(self, *args, **options):
        anidb = AniDB('mangakihttp', 1)
        anime = create_anime(**anidb.get_dict(options.get('id')))
        anime.retrieve_poster()  # Save for future use
        self.stdout.write(self.style.SUCCESS('Successfully added %s' % anime))
