import re
import html
import tempfile
from typing import List, Tuple, Optional

import time
from urllib.parse import urlparse

import aiohttp
from django.core.files import File
from django.core.management.base import BaseCommand
import xml.etree.ElementTree as ET

from mangaki import settings
from mangaki.models import Work
import asyncio
from aiohttp import ClientSession, BasicAuth
import os

from mangaki.utils.mal import _encoding_translation, MALEntry, MALWorks, MALClient

MAX_BACKOFF = 3600 * 2


def compute_backoff(backoff_time: float, max_backoff: float):
    return min(max_backoff, 2 * (backoff_time or 1))


class Command(BaseCommand):
    help = "Bulk fetch posters from MAL."

    def add_arguments(self, parser):
        parser.add_argument('-r', '--requests-per-batch',
                            default=3,
                            help='How many requests per batch (simultaneous) are done (be polite.)')
        parser.add_argument('-c', '--category-slug',
                            default='anime',
                            help='Which category slug to select, e.g. anime, manga, album')
        parser.add_argument('-v', '--verbose',
                            action='store_true',
                            help='Show more information about process')

    async def fetch_work(self, session: ClientSession, work: Work, retry_time: float = 0.5) -> Optional[
        Tuple[Work, MALEntry]]:
        work_type = MALWorks(work.category.slug)
        try:
            async with session.get(MALClient.SEARCH_URL.format(type=work_type.value),
                                   params={
                                       'q': work.title
                                   }) as response:
                try:
                    data = (await response.read())
                    text = data.decode('utf8')
                    if text == 'Invalid credentials':
                        raise RuntimeError('Invalid credentials')

                    if response.status == 204 or response.status == 400:  # No Content.
                        self.stdout.write(
                            self.style.ERROR('Request for {} failed.'.format(str(work))))
                        return None

                    if response.status == 403:
                        self.stdout.write(
                            self.style.WARNING('Too many requests. Sleeping during {} sec.'.format(retry_time)))
                        await asyncio.sleep(retry_time)
                        return await self.fetch_work(session, work,
                                                     compute_backoff(retry_time, MAX_BACKOFF))

                    html_code = html.unescape(re.sub(r'&amp;([A-Za-z]+);', r'a\1;', text))
                    xml = re.sub(r'&([^alg])', r'&amp;\1', _encoding_translation(html_code))
                    entry = MALEntry(ET.fromstring(xml).find('entry'), work_type)
                    await self.fetch_poster(session, work, entry.poster)
                    self.stdout.write(
                        self.style.SUCCESS('Fetched {} successfully.'.format(work.title))
                    )
                    return work, entry
        except aiohttp.client_exceptions.ClientResponseError:
            self.stdout.write(
                self.style.ERROR('Request for: {} failed.'.format(work)))
            return None

    def write_poster(self, poster_data: bytes, url: str, work: Work):
        try:
            filename = os.path.basename(urlparse(url).path)
            with tempfile.TemporaryFile() as f:
                f.write(poster_data)
                work.int_poster.save(filename, File(f))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR('Failure to write poster: {}'.format(e)))

    async def fetch_poster(self, session: ClientSession, work: Work, poster_link: str):
        loop = asyncio.get_event_loop()
        async with session.get(poster_link) as response:
            try:
                data = await response.read()
                loop.run_in_executor(None, self.write_poster, data, poster_link, work)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR('Failure to fetch poster: {}'.format(e)))

    async def fetch_posters(self, amount_of_simultaneous_requests: int, targets: List[Work]):
        tasks = []
        mal_entries = []

        async with ClientSession(
            auth=BasicAuth(login=settings.MAL_USER, password=settings.MAL_PASS),
            headers={
                'User-Agent': 'mangaki-async/0.2'
            }
        ) as session:
            for i in range(0, len(targets), amount_of_simultaneous_requests):
                start_time = time.time()
                for work in targets[i:i + amount_of_simultaneous_requests]:
                    task = asyncio.ensure_future(self.fetch_work(session, work))
                    tasks.append(task)

                mal_entries.extend(await asyncio.gather(*tasks))
                elapsed = time.time() - start_time
                self.stdout.write(
                    self.style.INFO('\nProcessed {} works in {} sec.'.format(len(tasks), elapsed)))
                tasks = []

            mal_entries = list(filter(None, mal_entries))
            self.stdout.write(
                self.style.INFO('Processed {} entries.'.format(len(mal_entries))))

    def handle(self, *args, **options):
        req_per_batch = options['requests_per_batch']
        slug = options['category_slug']
        self.verbose = options['verbose']
        targets = Work.objects.filter(int_poster='', category__slug=slug).select_related('category').all()
        self.stdout.write('Amount of work: {} objects.'.format(len(targets)))

        loop = asyncio.get_event_loop()
        future = asyncio.ensure_future(self.fetch_posters(req_per_batch, targets))
        loop.run_until_complete(future)
        self.stdout.write(self.style.SUCCESS('Successfully fetched all posters.'))
