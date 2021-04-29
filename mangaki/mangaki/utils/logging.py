# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from logging import Formatter


def set_advanced_formatting(handler):
    formatter = Formatter('%(asctime)s - [%(name)s] - %(levelname)s: %(message)s')
    handler.setFormatter(formatter)
