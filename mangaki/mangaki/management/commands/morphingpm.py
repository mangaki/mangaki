from django.core.management.base import BaseCommand, CommandError

import json
from mangaki.utils.values import tags_definition
from math import floor
import numpy as np

posters = json.load(open('../fixtures/mangaki_i2v.json'))
nb_tags = len(tags_definition)
index_posters = [.0] * len(posters)
i = 0
for poster in posters:
	index = int(poster[:len(poster)-4])
	index_posters[i] = index
	i += 1
poster_tags = np.zeros((max(index_posters)+1, nb_tags))
for poster in posters:
	index = int(poster[:len(poster)-4])
	for tag, value in posters[poster]['general']:
		poster_tags[index][tags_definition[tag]] = value

def distance(a, b):
	dist = (b - a)
	return np.linalg.norm(dist)

def morphing(a, b, subdiv = 3):
	segment = poster_tags[b] - poster_tags[a]
	seg_norm = np.linalg.norm(segment)
	sub_middles = np.zeros((subdiv, nb_tags))
	for i in range(subdiv):
		sub_middles[i] = poster_tags[a] + segment * (i+1/2)/(subdiv)
	morphism = [0] * (subdiv+2)
	morphism[0] = a
	morphism[subdiv+1] = b
	nb_posters = poster_tags.shape[0]
	for i in range (nb_posters):
		# if the selected poster is in fact a poster and is neither the goal or the beginning
		if i!=a and i!=b and i in index_posters:
			current = poster_tags[i] - poster_tags[a]
			projection = np.dot(current, segment)/seg_norm
			# if the projection is contained in the segment
			if projection > 0 and projection < seg_norm:
				# sub_in is the subdivision the selected poster is in
				sub_in = floor((projection/seg_norm) * subdiv) + 1
				# if there is no point for the subdivision, or if selected poster is nearer than currently chosen poster
				if morphism[sub_in]==0 or distance(sub_middles[sub_in-1], poster_tags[i]) < distance(sub_middles[sub_in-1], poster_tags[morphism[sub_in]]):
					morphism[sub_in] = i
	return morphism

class Command(BaseCommand):
    args = ''
    help = 'Make morphing between 2 posters'

    def add_arguments(self, parser):
        parser.add_argument('myargs', nargs='+', type=str)

    def handle(self, *args, **options):
    	a = int(options['myargs'][0])
    	b = int(options['myargs'][1])
    	if len(options['myargs'])==2:
    		print(morphing(a, b))
    	else:
    		subdiv = int(options['myargs'][2])
    		print(morphing(a, b, subdiv))