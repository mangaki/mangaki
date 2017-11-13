from mangaki.algo import RecommendationAlgorithm, register_algorithm
from sklearn.ensemble import GradientBoostingRegressor as GBR
from mangaki.algo.als import MangakiALS
from mangaki.algo.dataset import Dataset
from django.conf import settings
import json
import numpy as np
import os.path


I2V_DIR = os.path.join(settings.DATA_DIR, 'illustration2vec')


@register_algorithm('gbr')
class MangakiGBR(RecommendationAlgorithm):
	U = None
	M = None
	dataset = Dataset()
	def __init__(self, NB_COMPONENTS=10, NB_ITERATIONS=10, LAMBDA=0.1):
		super().__init__()
		self.NB_COMPONENTS = NB_COMPONENTS
		self.NB_ITERATIONS = NB_ITERATIONS
		self.LAMBDA = LAMBDA

	def load(self, filename):
		backup = super().load(filename)
		self.M = backup.M
		self.U = backup.U
		self.dataset.load('rating' + self.get_backup_filename())

	def fit(self, X, y):
		als_algo = MangakiALS(20)
		als_algo.set_parameters(self.nb_users,self.nb_works)
		als_algo.fit(X, y)
		tags = json.load(open(os.path.join(I2V_DIR, 'mangaki_i2v.json')))
		self.chrono.save("fitting als algo")
		V = np.transpose(als_algo.VT)

		try:
			tags_definition = json.load(open(os.path.join(I2V_DIR, 'all_tags.json')))
		except FileNotFoundError:
			tags = json.load(open(os.path.join(I2V_DIR, 'mangaki_i2v.json')))
			all_tags = set()
			for poster in tags:
				all_tags.update([tag for tag, _ in tags[poster]['general']])
			tags_definition = {}
			i = 0
			for tag in all_tags:
				tags_definition[tag] = i
				i += 1

			json.dump(tags_definition, open(os.path.join(I2V_DIR, 'all_tags.json'), 'w'))

		nb_tags = len(tags_definition)
		poster_tags = np.zeros((self.nb_works, nb_tags))
		for i in range(self.nb_works):
			poster = str(self.dataset.decode_work[i])+'.jpg'
			if poster in tags:
				for tag, value in tags[poster]['general']:
					poster_tags[i][tags_definition[tag]] = value
		i = 0
		for (user_id, work_id) in X:
			self.U = np.zeros((len(y), als_algo.U.shape[1]+V.shape[1]+nb_tags))
			iline = []
			iline.extend(als_algo.U[user_id])
			iline.extend(V[work_id])
			iline.extend(poster_tags[work_id])
			self.U[i] = iline
		self.M = GBR()
		self.M.fit(self.U,y)

	def predict(self,X):
		X_selected = set()
		for user_id in X:
			X_selected.update([user_id[0]])
		return self.M.predict(self.U[list(X_selected)])

	def load_dataset(self, to_load):
		self.dataset = to_load

	def get_shortname(self):
		return 'gbr-%d' % self.NB_COMPONENTS
