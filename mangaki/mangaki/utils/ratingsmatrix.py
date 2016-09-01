from scipy.sparse import csc_matrix
from mangaki.utils.values import rating_values
import pandas


class RatingsMatrix:

    def __init__(self, qs=None, fname=None):
        user_list, item_list, data = [], [], []
        if fname is None:
            if qs is None:
                raise ValueError('one of fname or qs must be non None')
            else:
                content = qs
                for user_id, item_id, rating in content:
                    user_list.append(user_id)
                    item_list.append(item_id)
                    data.append(rating_values[rating])
        else:
            content = pandas.read_csv(fname,
                                      header=None).as_matrix()
            for user_id, item_id, rating in content:
                user_list.append(user_id)
                item_list.append(item_id)
                data.append(rating_values[rating])
        self.user_set = set(user_list)
        self.item_set = set(item_list)
        self.user_dict = {v: k for k, v in enumerate(self.user_set)}
        self.item_dict = {v: k for k, v in enumerate(self.item_set)}
        self.user_dict_inv = dict(enumerate(self.user_set))
        self.item_dict_inv = dict(enumerate(self.item_set))
        row = [self.user_dict[v] for v in user_list]
        col = [self.item_dict[v] for v in item_list]
        matrix = csc_matrix((data, (row, col)), shape=(
            len(self.user_set), len(self.item_set)))
        self.matrix = matrix
