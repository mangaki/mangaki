# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-06-10 11:45
from __future__ import unicode_literals

from django.db import migrations
from mangaki.models import UNK_LANG_VALUE

# AniDB → ISO639-1 or custom.
anidb_lang_map = {
    'al': 'sq',
    'ar': 'ar',
    'bd': 'bn',
    'pt-BR': 'pt',
    'bg': 'bg',
    'ca': 'ca',
    'zh-x-yue': 'zh',
    'zh-x-cmn': 'zh',
    'zh-Hans': 'zh',
    'zh-x-nan': 'zh',
    'zh-Hant': 'zh',
    'zh': 'zh',
    'hr': 'hr',
    'cs': 'cs',
    'da': 'da',
    'nl': 'nl',
    'en': 'en',
    'et': 'et',
    'fi': 'fi',
    'fr': 'fr',
    'gl': 'gl',
    'ka': 'ka',
    'de': 'de',
    'el': 'el',
    'he': 'he',
    'hu': 'hu',
    'is': 'is',
    'id': 'id',
    'x-in': 'x-in',  # Instrumental
    'it': 'it',
    'ja': 'ja',
    'x-jat': 'x-jat',  # x-jat is transliteral Japanese
    'jv': 'jv',
    'ko': 'ko',
    'x-kot': 'x-kot',  # x-kot is transliteral Korean
    'la': 'la',
    'es-LA': 'la',
    'lv': 'lv',
    'lt': 'lt',
    'my': 'ms',
    'no': 'no',
    'pl': 'pl',
    'pt': 'pt',
    'ro': 'ro',
    'ru': 'ru',
    'sr': 'sr',
    'sk': 'sk',
    'sl': 'sl',
    'es': 'es',
    'sv': 'sv',
    'ta': 'ta',
    'tt': 'tt',
    'th': 'th',
    'tr': 'tr',
    'uk': 'uk',
    'x-unk': UNK_LANG_VALUE,
    'x-other': UNK_LANG_VALUE,
    'vi': 'vi'
}


def add_languages(apps, schema):
    Language = apps.get_model('mangaki', 'Language')
    db_alias = schema.connection.alias
    extended_iso639_langs = [
        Language(code=extended_iso639)
        for extended_iso639 in set(anidb_lang_map.values())
    ]

    extended_iso639_langs.append(
        Language(code='x-simple')
    )
    languages = Language.objects.using(db_alias).bulk_create(extended_iso639_langs)
    lang_model_map = {lang.code: lang for lang in languages}

    ExtLanguage = apps.get_model('mangaki', 'ExtLanguage')

    # AniDB
    ExtLanguage.objects.using(db_alias).bulk_create([
        ExtLanguage(source='anidb', ext_lang=x,
                    lang=lang_model_map[y])
        for x, y in anidb_lang_map.items()
    ])

    # MAL, refer to mangaki/utils/mal.py to understand `ext_lang` values.
    ExtLanguage.objects.using(db_alias).bulk_create([
        ExtLanguage(source='mal', ext_lang='unknown',
                    lang=lang_model_map[None]),
        ExtLanguage(source='mal', ext_lang='english',
                    lang=lang_model_map['en'])
    ])


class Migration(migrations.Migration):
    dependencies = [
        ('mangaki', '0071_ext_language'),
    ]

    operations = [
        migrations.RunPython(add_languages, migrations.RunPython.noop)
    ]
