from logging import Formatter


def set_advanced_formatting(handler):
    formatter = Formatter('%(asctime)s - [%(name)s] - %(levelname)s: %(message)s')
    handler.setFormatter(formatter)
