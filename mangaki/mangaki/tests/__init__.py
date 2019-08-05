import logging

logging.getLogger('tensorflow').disabled = True
logging.getLogger('chardet.charsetprober').setLevel(logging.INFO)
