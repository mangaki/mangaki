from django.core.management.base import BaseCommand, CommandError

import os
import json
from math import floor
import numpy as np
from mangaki.settings import DATA_DIR
from zero.side import SideInformation


def load_poster_tags():
    side = SideInformation()
    return side.nb_tags, side.T

def distance(a, b):
    dist = (b - a)
    return np.linalg.norm(dist)

def dist2seg(point, a, segment):
    seg_norm = np.linalg.norm(segment)
    current = point - a
    projection = np.dot(current, segment)/seg_norm
    dist2seg = distance(a, point)**2 - projection**2
    return np.sqrt(dist2seg)

def morphing(a, b, subdiv = 4):
    _, poster_tags = load_poster_tags()
    segment = poster_tags[b] - poster_tags[a]
    seg_norm = np.sqrt(np.dot(segment, segment))
    subdiv_length = seg_norm/subdiv    
    morphism = [0] * (subdiv+1)
    morphism[0] = a
    morphism[subdiv] = b
    nb_posters = poster_tags.shape[0]
    for i in range (nb_posters):
        # if the selected poster is in fact a poster and is neither the goal or the beginning
        if i != a and i != b:
            current = poster_tags[i] - poster_tags[a]
            projection = np.dot(current, segment)/seg_norm
            # if the projection is contained in the segment [a,b] with a subdiv/2 offset for more diverse morphing
            if projection > subdiv_length/2 and projection < seg_norm-subdiv_length/2:
                # sub_in is the subdivision the selected poster is in
                sub_in = floor(((projection-subdiv_length/2)/seg_norm) * subdiv) + 1
                # if there is no point for the subdivision, or if selected poster is nearer than currently chosen poster
                if morphism[sub_in]==0 or dist2seg(poster_tags[i], poster_tags[a], segment) < dist2seg(poster_tags[morphism[sub_in]], poster_tags[a], segment):
                    morphism[sub_in] = i
    return morphism

def morphing2(a, b, subdiv = 4):
    nb_tags, poster_tags = load_poster_tags()
    segment = poster_tags[b] - poster_tags[a]
    seg_norm = np.linalg.norm(segment)
    sub_middles = np.zeros((subdiv-1, nb_tags))
    subdiv_length = seg_norm/subdiv    
    for i in range(subdiv-1):
        sub_middles[i] = poster_tags[a] + segment * (i+1)/(subdiv)
    morphism = [0] * (subdiv+1)
    morphism[0] = a
    morphism[subdiv] = b
    nb_posters = poster_tags.shape[0]
    for i in range (nb_posters):
        # if the selected poster is in fact a poster and is neither the goal or the beginning
        if i!=a and i!=b:
            current = poster_tags[i] - poster_tags[a]
            projection = np.dot(current, segment)/seg_norm
            # if the projection is contained in the segment [a,b] with a subdiv/2 offset for more diverse morphing
            if projection > subdiv_length/2 and projection < seg_norm-subdiv_length/2:
                # sub_in is the subdivision the selected poster is in
                sub_in = floor(((projection-subdiv_length/2)/seg_norm) * subdiv) + 1
                # if there is no point for the subdivision, or if selected poster is nearer than currently chosen poster
                if morphism[sub_in]==0 or distance(sub_middles[sub_in-1], poster_tags[i]) < distance(sub_middles[sub_in-1], poster_tags[morphism[sub_in]]):
                    morphism[sub_in] = i
    return morphism

class Command(BaseCommand):
    args = ''
    help = 'Make morphing between 2 posters'

    def add_arguments(self, parser):
        parser.add_argument('work_ids', nargs=2, type=str)
        parser.add_argument('--other', action='store_true', help='Try another algorithm', default=False)
        parser.add_argument('--n', type=int, help='Number of subdivisions', default=4)

    def handle(self, *args, **options):
        a = int(options['work_ids'][0])
        b = int(options['work_ids'][1])
        other_algorithm = options['other']
        subdiv = options['n']
        
        if other_algorithm:
            work_ids = morphing2(a, b, subdiv)
        else:
            work_ids = morphing(a, b, subdiv)
        self.stdout.write(','.join(str(work_id) for work_id in work_ids))
