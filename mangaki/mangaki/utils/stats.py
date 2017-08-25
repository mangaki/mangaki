import math

def avgstd(l):  # Displays mean and variance
    n = len(l)
    mean = float(sum(l)) / n
    var = float(sum(i * i for i in l)) / n - mean * mean
    return '%.5f ± %.5f' % (round(mean, 5), round(1.96 * math.sqrt(var / n), 3))  # '%.3f ± %.3f' % 