# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

import logging
import numpy as np

from django.test import TestCase
from mangaki.utils.dpp import MangakiDPP


class DPPTest(TestCase):
    def setUp(self):
        work_ids = [2, 4, 6]
        self.nb_works = len(work_ids)
        nb_components = 20
        vectors = np.random.random((self.nb_works, nb_components))
        self.dpp = MangakiDPP(work_ids, vectors)

    def test_dpp(self):
        self.dpp.compute_similarity()
        self.dpp.preprocess()
        subset = self.dpp.sample_k(self.nb_works)
        self.assertEqual(set(subset), set(self.dpp.work_ids))
