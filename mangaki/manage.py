#!/usr/bin/env python
# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mangaki.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
