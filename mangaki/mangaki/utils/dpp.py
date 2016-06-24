#remettre le all_dataset
from scipy.sparse import csc_matrix
from scipy.spatial.distance import pdist, squareform
from mangaki.utils.svd import MangakiSVD
from mangaki.utils.values import rating_values
from mangaki.models import Rating
import pandas, random
import numpy as np

#source : from 'csv' or 'database' ?

#from csv
"""
ratings = pandas.read_csv('../data/ratings.csv', header=None).as_matrix()	
nb_users = ratings[:,0].max()+1
nb_items = ratings[:,1].max()+1
items = range(0,nb_items)

"""

#from database
X, Y = [], []
for user_id, work_id, choice in Rating.objects.values_list('user_id', 'work_id', 'choice'):
	X.append([user_id, work_id])
	Y.append(rating_values[choice])
X=np.asarray(X)
nb_users = X[:,0].max()+1
nb_items = X[:,1].max()+1
items = range(0,nb_items)



#2 fonctions donnant une matrice de départ user*item
"""
récupérer une matrice users*items avec les 1er nb_ratings de ratings.csv
-soit SVD ayant pour rang rank	
-soit matrice creuse ayant pour coeff les ratings (creuse[i][j]=rating de l'utilisateur i pour l'oeuvre j)
"""
def get_matrix_svd(rank, nb_ratings):
	Xpr = X[:nb_ratings,0:2]
	Ypr = Y[:nb_ratings]
	svd = MangakiSVD(rank) 
	svd.set_parameters(nb_users,nb_items)
	svd.fit(Xpr,Ypr)
	return svd.VT



def get_matrix_csc(nb_ratings): 
		row = X[:nb_ratings,0]
		col = X[:nb_ratings,1]
		data = np.array(Y[:nb_ratings])
		creux = csc_matrix((data, (row, col)), shape=(nb_users, nb_items))
		creuse = creux.toarray()
		return creuse     


#2 fonctions calculant des matrices de similarité

#prendre en argument une metric car pas très intéressant car déjà tt fait en Python

#option = 'cosine' pr 'jaccard'
def similarity(matrix, option): # matrix: dimension nb_users x dimension nb_works
    return 1 - squareform(pdist(matrix.T, metric=option))
	
class MangakiUniform(object):
	
	def __init__(self, nb_points):
		self.nb_points = nb_points


	def sample_k(self,matrix_similarity):
		uniform_items = list(range(matrix_similarity.shape[0]))
		random.shuffle(uniform_items)
		return uniform_items[:self.nb_points]
    	
	def __str__(self):
		return 'uniform list, nb_points=%d' % self.nb_points

class MangakiDPP(object):

	def __init__(self, nb_points):
		self.nb_points = nb_points


#n'a pas d'intérêt au final
#TODO : delete
#similarity_fn='jaccard' or 'coisine'
#def fit(self, matrix, all_dataset=False): #obtention de la matrice de similarité
#	matrix_fit=similarity(matrix, similarity_fn)
#	return matrix_fit
    
#thanks to mehdidc on github
# tirer au hasard des points
#def sample_k(items, similiarity, k, max_nb_iterations=1000, rng=np.random):
       #def sample_k(items, similiarity, k, max_nb_iterations=1000, rng=np.random):
	def sample_k(self, items, L, k, max_nb_iterations=1000, rng=np.random):
	
	#Sample a list of k items from a DPP defined
	#by the similarity matrix L. The algorithm
	#is iterative and runs for max_nb_iterations.
	#The algorithm used is from
	#(Fast Determinantal Point Process Sampling withw
	#Application to Clustering, Byungkon Kang, NIPS 2013)
	
		initial = rng.choice(range(len(items)), size=k, replace=False)
		X = [False] * len(items)
		for i in initial:
			X[i] = True
		X = np.array(X)
		for i in range(max_nb_iterations):
			u = rng.choice(np.arange(len(items))[X])
			v = rng.choice(np.arange(len(items))[~X])
			Y = X.copy()
			Y[u] = False
			L_Y = L[Y, :]
			L_Y = L_Y[:, Y]
			L_Y_inv = np.linalg.inv(L_Y)

			c_v = L[v:v+1, :]
			c_v = c_v[:, v:v+1]
			b_v = L[Y, :]
			b_v = b_v[:, v:v+1]
			c_u = L[u:u+1, :]
			c_u = c_u[:, u:u+1]
			b_u = L[Y, :]
			b_u = b_u[:, u:u+1]

			p = min(1, c_v - np.dot(np.dot(b_v.T, L_Y_inv), b_v) /
	              (c_u - np.dot(np.dot(b_u.T, L_Y_inv.T), b_u)))
			if rng.uniform() <= p:
				X = Y[:]
				X[v] = True
			return np.array(items)[X]
      
    
	def __str__(self):
		return 'sample dpp list, nb_points=%d' % self.nb_points
   

# comparer : regarder la distance moyenne entre deux points, mesures de dispersion. Avoir un truc qui permet de faire le fit + lancer quelques milliers de samples et regarder la dispersion moyenne
#ajouter des options : quels para de comparaison utilisés ? Diamètre d'ordre r (1 ou 0 ? ), somme de pdist, déterminant du squareform(pdsit) ?


#(pdist(svd.VT[:,sampled_items].T)).sum()

"""
distance_sample = []
distance_uniform = []
et ds la boucle : 
distance_sample.append((pdist(svd.VT[:,sampled_items].T)).sum())
distance_uniform.append((pdist(svd.VT[:,uniform_items].T)).sum())
puis comparaison entre les deux listes d'une manière ou d'une autre
"""


#det de pdist : np.linalg.det(squareform(pdist(svd.VT[:,uniform_items].T, metric='cosine')))

#diamètre d'ordre r : (ici 1 pr l'instant) 
"""
n = len(sampled_items)
coefficient_sample = 2/(n*(n-1))*(pdist(svd.VT[:,sampled_items].T).sum())
"""




def compare(type_get_matrix, nb_points, nb_iterations, nb_ratings):
	results_uniform, results_sample_dpp=[], []
	if type_get_matrix=='svd':

		matrix = get_matrix_svd(10, nb_ratings)
	else :
		matrix = get_matrix_csc(10, nb_ratings)
	uniform = MangakiUniform(nb_points)
	dpp = MangakiDDP(10)#nb_points ne sert à rien 
	similarity1=similarity(matrix,'cosine')
	indicateur = 0
	pb = 0
	while indicateur != nb_iterations:
    
		try:
			sampled_items = dpp.sample_k(items, similarity, nb_points)
        

		except np.linalg.linalg.LinAlgError as err:
			pb = 1
		if pb==0:
			indicateur = indicateur+1
        # cas où tt se passe bien, bloc où l'on exécute la comparaison
			uniform_items = uniform.sample_k(similarity)
        	
			det_uni=np.linalg.det(squareform(pdist(svd.VT[:,uniform_items].T, metric='cosine')))
			det_dpp=np.linalg.det(squareform(pdist(svd.VT[:,sampled_items].T, metric='cosine')))
        	
			diam_uni = 2/(nb_points*(nb_points-1))*(pdist(svd.VT[:,uniform_items].T).sum())
			diam_dpp = 2/(nb_points*(nb_points-1))*(pdist(svd.VT[:,sampled_items].T).sum())

			results_uniform.append([det_uni, diam_uni]) #à compléter : det et diamètre d'ordre r
			results_sample_dpp.append([det_dpp, diam_dpp]) #à compléter : det et diamètre d'ordre r
		else :
			pb = 0






