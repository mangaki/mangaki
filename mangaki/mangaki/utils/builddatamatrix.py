from sklearn.utils.extmath import randomized_svd
from scipy.spatial.distance import pdist, squareform
from scipy.sparse import csc_matrix
from numpy.random import choice
from mangaki.utils.values import rating_values
from mangaki.models import Rating
import pandas
import random
import numpy as np

def build_matrix(fname=None):
    user_list, item_list, data = [],[], []


    if fname is None:
        content = Rating.objects.values_list('user_id',
                                             'work_id',
                                             'choice')
        for user_id, item_id, choice in content:
            user_list.append(user_id)
            item_list.append(item_id)
            data.append(rating_values[choice])
    else:
        content = pandas.read_csv(fname,
                                  header=None).as_matrix()
        for user_id, item_id, choice in content:
            user_list.append(user_id)
            item_list.append(item_id)
            data.append(rating_values[choice])
        
    user_set=set(user_list)
    item_set=set(item_list)
    user_dict = {v: k for k, v in enumerate(user_set)}
    item_dict = {v: k for k, v in enumerate(item_set)}
    row=[user_dict[v] for v in user_list]
    col=[item_dict[v] for v in item_list]
    matrix = csc_matrix((data, (row, col)), shape=(len(user_set),len(item_set))).toarray()
    return matrix, user_dict, item_dict, user_set, item_set

