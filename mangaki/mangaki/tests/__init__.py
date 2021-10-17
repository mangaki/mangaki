# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

import logging

logging.getLogger('tensorflow').disabled = True
logging.getLogger('chardet.charsetprober').setLevel(logging.INFO)
