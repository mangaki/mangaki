from mangaki.utils.common import RecommendationAlgorithm
from sklearn.ensemble import GradientBoostingRegressor as GBR
from mangaki.utils.als import MangakiALS
from mangaki.utils.data import Dataset
from mangaki.utils.values import tags_definition
import json
import numpy as np

class  MangakiGBR(RecommendationAlgorithm):
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
		tags = json.load(open('../fixtures/mangaki_i2v.json'))
		self.chrono.save("fitting als algo")
		V = np.transpose(als_algo.VT)
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