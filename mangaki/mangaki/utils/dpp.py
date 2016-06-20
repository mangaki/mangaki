#matrice svd au début ou matrice user*item ?
#importer sample_k
#fit, predict : voir knn, svd
#€voir get_reco de svd
from scipy.spatial.distance import pdist, squareform
import random



def cosine_similarity(X): # X : dimension nb_works x dimension latente
    return 1 - squareform(pdist(X, metric='cosine'))


class MangakiUniform(object):
	nb_points=None
	matrix_similarity=None
	def __init__(self, nb_points, matrix_similarity) :
    	self.nb_points=nb_points
    	self.matrix_similarity=matrix_similarity

    def sample_uniform(self):
		uniform_items = list(range(matrix_similarity.shape[0]))
		random.shuffle(uniform_items)
		return uniform_items[:size]
    	

	def __str__(self):
		return 'uniform list, nb_points=%d' % self.nb_points

class MangakiDPP(object):
	def __init__(self, similarity) :
		pass
		#à compléter

	def __str__(self):
		pass

	
    def fit(self, X, y, similarity_fn=cosine_similarity, all_dataset=False):
        # si all_dateset alors aller chercher dans la bdd
        X = [(user_id, work_id)]
        y = [ratings]
        # calculer la matrice de similarite des oeuvres
        #...
        self.mat = mat
    
    def sample_k(self, k=10):
        # tirer au hasard des points
    #def sample_k(items, similiarity, k, max_nb_iterations=1000, rng=np.random):
    

ddp = MangakiDDP(similarity='cosine', latent_dim=10)
ddp.fit(ratings)

sampled_ratings = ddt.sample_k(10)

# comparer : regarder la distance moyenne entre deux points, mesures de dispersion. Avoir un truc qui permet de faire le fit + lancer quelques milliers de samples et regarder la dispersion moyenne
def compare:
	pass
#fit, milliers de sample

# integrer avec la page d'accueil qui propose des nouveaux animes : voir views, il faudra changer random



	
	