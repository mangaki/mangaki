from collections import Counter
import json
import time
import os
import argparse

from django.core.management.base import BaseCommand
from django.conf import settings
from mangaki.models import Work

import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist, squareform
from PIL import Image, ImageFont, ImageDraw


# def create_collage(width, height, listofimages):
#     cols = len(listofimages)
#     collage = Image.new('RGBA', (width*len(listofimages), height))
#     draw = ImageDraw.Draw(collage)
#     names = [os.path.relpath(os.path.splitext(path)[0], 'posters') for path in listofimages]
#
#     ims = []
#     for p in listofimages:
#         im = Image.open(p)
#         im.thumbnail((width, height))
#         ims.append(im)
#
#     x = 0
#     for col in range(cols):
#         if col == 1:
#             x += 5
#
#         pos_x = int(x+(width-ims[col].width)/2)
#         pos_y = height-ims[col].height
#         collage.paste(ims[col], (pos_x, pos_y))
#
#         text_w, text_h = draw.textsize(names[col])
#         text_x = int(pos_x + (ims[col].width-text_w)/2)
#         text_y = height-25
#
#         draw.text((text_x-1, text_y-1), names[col], fill=(255,255,255))
#         draw.text((text_x+1, text_y-1), names[col], fill=(255,255,255))
#         draw.text((text_x-1, text_y+1), names[col], fill=(255,255,255))
#         draw.text((text_x+1, text_y+1), names[col], fill=(255,255,255))
#         draw.text((text_x, text_y), names[col], (0,0,0))
#
#         x += width
#
#     draw.line((width,0,width,height), fill=(0,0,0), width=5)
#
#     if not os.path.exists('collages'):
#         os.makedirs('collages')
#     collage.save('collages/collage_{}.png'.format(names[0]))

NUMBER_CLOSESTS = 5
CATEGORY_WEIGHTS = {'character': 1, 'rating': 1, 'general': 1, 'copyright': 1}
SAVE_FILE = 'posters_neighborships.pkl'

class Command(BaseCommand):
    help = 'Find closest neighbors to a poster for a work'

    def add_arguments(self, parser):
        parser.add_argument('poster_id', nargs=1, type=int)

    def handle(self, *args, **options):
        id_wanted = options['poster_id'][0]
        poster_wanted = '{}.jpg'.format(id_wanted)

        # Try to retrieve already saved neighborship information
        if os.path.isfile(SAVE_FILE):
            neighborship = pd.read_pickle(SAVE_FILE)
            self.stdout.write('Loaded neighborship data from pickle\n')
        else:
            # Open the JSON i2v file
            with open(os.path.join(settings.DATA_DIR, 'mangaki_i2v.json'), encoding='utf-8') as f_i2v:
                i2v = json.load(f_i2v)

            # Let's make a {poster_id: tags} dict to simplify things up
            processed_data = {}
            for poster in i2v:
                tags_dict = {}
                poster_id = int(os.path.splitext(poster)[0])
                for category, tags in i2v[poster].items():
                    for tag, weight in tags:
                        tags_dict[tag] = weight * CATEGORY_WEIGHTS[category]
                processed_data[poster_id] = tags_dict

            # Calculate euclidean distances poster to poster
            self.stdout.write('Calculating matrix of euclidean distances ...')
            start_time = time.time()
            df = pd.DataFrame(processed_data).fillna(0).transpose()
            q = squareform(pdist(df, 'euclidean'))
            neighborship = pd.DataFrame(q, index=df.index, columns=df.index)
            self.stdout.write('Compute time : '+str(time.time()-start_time))

            # And finally save those for later
            # neighborship.to_pickle(SAVE_FILE)
            # self.stdout.write('Saved neighborship data to pickle\n')

        # Make a collage of images for each poster passed as an argument

        if id_wanted in neighborship:
            closests = neighborship[id_wanted].sort_values('index').axes[0].tolist()[1:NUMBER_CLOSESTS+1]
            self.stdout.write('Closest to {} : {}'.format(id_wanted, ', '.join(list(map(str, closests)))))

            # listofimages = ['posters/'+str(name)+'.jpg' for name in closests]
            # create_collage(90, 150, listofimages)
        else:
            self.stdout.write('Could not find {} ...'.format(id_wanted))
