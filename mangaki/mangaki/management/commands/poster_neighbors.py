import json
import time
import os

from django.core.management.base import BaseCommand
from django.conf import settings

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import euclidean_distances
from PIL import Image, ImageFont, ImageDraw


NUMBER_CLOSESTS = 5
CATEGORY_WEIGHTS = {'character': 1, 'rating': 1, 'general': 1, 'copyright': 1}

def create_collage(width, height, poster_ids):
    cols = len(poster_ids)
    collage = Image.new('RGB', (width*cols, height))
    draw = ImageDraw.Draw(collage)
    filenames = [os.path.join(settings.STATIC_ROOT, 'img/posters/{}.jpg'.format(pid)) for pid in poster_ids]

    ims = []
    for poster in filenames:
        im = Image.open(poster)
        im.thumbnail((width, height))
        ims.append(im)

    x = 0
    for col in range(cols):
        if col == 1:
            x += 5

        pos_x = int(x+(width-ims[col].width)/2)
        pos_y = height-ims[col].height
        collage.paste(ims[col], (pos_x, pos_y))

        text_w, text_h = draw.textsize(str(poster_ids[col]))
        text_x = int(pos_x + (ims[col].width-text_w)/2)
        text_y = height-25

        draw.text((text_x-1, text_y-1), str(poster_ids[col]), fill=(255,255,255))
        draw.text((text_x+1, text_y-1), str(poster_ids[col]), fill=(255,255,255))
        draw.text((text_x-1, text_y+1), str(poster_ids[col]), fill=(255,255,255))
        draw.text((text_x+1, text_y+1), str(poster_ids[col]), fill=(255,255,255))
        draw.text((text_x, text_y), str(poster_ids[col]), (0,0,0))

        x += width

    draw.line((width,0,width,height), fill=(0,0,0), width=5)

    collages_path = os.path.join(settings.STATIC_ROOT, 'img/posters_collages')
    if not os.path.exists(collages_path):
        os.makedirs(collages_path)
    collage.save(os.path.join(settings.STATIC_ROOT, 'img/posters_collages/collage_{}.jpg'.format(poster_ids[0])))


class Command(BaseCommand):
    help = "Find closest posters neighbors to a work's poster"

    def add_arguments(self, parser):
        parser.add_argument('poster_id', nargs=1, type=int)
        parser.add_argument('--collage', dest='collage', action='store_true')

    def handle(self, *args, **options):
        id_wanted = options['poster_id'][0]
        poster_wanted = '{}.jpg'.format(id_wanted)

        processed_data = {}
        df = None

        # Open the JSON i2v file
        with open(os.path.join(settings.DATA_DIR, 'mangaki_i2v.json'), encoding='utf-8') as f_i2v:
            i2v = json.load(f_i2v)

            # Let's make a {poster_id: tags} dict
            for poster in i2v:
                tags_dict = {}
                poster_id = int(os.path.splitext(poster)[0])
                for category, tags in i2v[poster].items():
                    for tag, weight in tags:
                        tags_dict[tag] = weight * CATEGORY_WEIGHTS[category]
                processed_data[poster_id] = tags_dict

            df = pd.DataFrame(processed_data).fillna(0).transpose()
            i2v = None
            processed_data = None

        if not id_wanted in df.index:
            self.stdout.write('Could not find {} ...'.format(id_wanted))
            return

        # Calculate euclidean distances from the wanted poster to all other posters
        distances = euclidean_distances(df.loc[id_wanted].values.reshape(1, -1), df)
        neighborship = pd.DataFrame(distances, index=[id_wanted], columns=df.index)
        distances = None

        # Display ID of neighbors for a poster and make a collage if flag passed as argument
        if id_wanted in neighborship:
            closests = neighborship.loc[id_wanted].sort_values('index').axes[0].tolist()[1:NUMBER_CLOSESTS+1]
            self.stdout.write(', '.join(list(map(str, closests))))

            if options['collage']:
                id_list = [id_wanted]
                id_list.extend(closests)
                create_collage(90, 150, id_list)
        else:
            self.stdout.write('Could not find {} ...'.format(id_wanted))
