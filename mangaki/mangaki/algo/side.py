from django.conf import settings
from scipy.sparse import load_npz, issparse
from sklearn.preprocessing import scale
import os.path


class SideInformation:
    def __init__(self, T=None, perform_scaling=True, with_mean=False):
        self.T = T
        self.nb_tags = None
        self.perform_scaling = perform_scaling
        self.with_mean = with_mean
        self.load()
        self.preprocess(self.perform_scaling, self.with_mean)

    def load(self):
        # Load in CSC format if no matrix provided.
        if self.T is None:
            self.T = load_npz(os.path.join(settings.DATA_DIR, 'lasso',
                                           'tag-matrix.npz')).tocsc()
        _, self.nb_tags = self.T.shape

    def preprocess(self, perform_scaling, with_mean):
        if perform_scaling:
            # Densify T to prevent sparsity destruction
            # (which will anyway result in an exception).
            if with_mean and issparse(self.T):
                self.T = self.T.toarray()

            self.T = scale(self.T, with_mean=with_mean, copy=False)

            # If it's still sparse, let's get a dense version.
            if issparse(self.T):
                self.T = self.T.toarray()
        else:
            self.T = self.T.toarray() if issparse(self.T) else self.T
