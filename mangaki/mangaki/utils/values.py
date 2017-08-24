import json

rating_values = {'favorite': 4, 'like': 2, 'dislike': -2, 'neutral': 0.1, 'willsee': 0.5, 'wontsee': -0.5}
rating_values_dpp = {'like': 2, 'dislike': -2, 'dontknow': 0}
# rating_values = {'favorite': 1, 'like': 1, 'neutral': 0, 'dislike': 0, 'willsee': 0, 'wontsee': 0}  # For NMF, do not use in production!

try:
	tags_definition = json.load(open('../fixtures/all_tags.json'))
except FileNotFoundError:
	tags = json.load(open('../fixtures/mangaki_i2v.json'))
	all_tags = set()
	for poster in tags:
		all_tags.update([tag for tag, _ in tags[poster]['general']])
	tags_definition = {}
	i = 0
	for tag in all_tags:
		tags_definition[tag] = i
		i += 1

	json.dump(tags_definition, open('../fixtures/all_tags.json', 'w'))