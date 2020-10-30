import numpy as np


def esym_poly(k, lam):
    N = lam.size
    E = np.zeros((k + 1, N + 1))
    E[0, :] = np.ones((1, N + 1))
    for l in range(1, k + 1):
        for n in range(1, N + 1):
            E[l, n] = E[l, n - 1] + lam[n - 1] * E[l - 1, n - 1]

    return E


def sample_k(k, lam, V_full):
    E = esym_poly(k, lam)
    J = []
    remaining = k - 1
    i = lam.size - 1

    while remaining >= 0:
        marg = 0.0
        if i == remaining:
            marg = 1.0
        else:
            if E[remaining + 1, i + 1] == 0:
                i = i - 1
                continue
            marg = lam[i] * E[remaining, i] / E[remaining + 1, i + 1]

        if np.random.rand() < marg:
            J.append(i)
            remaining = remaining - 1

        i = i - 1

    k = len(J) - 1
    Y = np.zeros((len(J), 1))
    V = V_full[:, J]

    for i in range(k, -1, -1):
        # Sample
        Pr = np.sum(V**2, axis=1)
        Pr = Pr / sum(Pr)
        C = np.cumsum(Pr)
        jj = np.argwhere(np.random.rand() <= C)[0]
        Y[i] = jj

        # Update V
        j = np.argwhere(V[int(Y[i]), :])[0]
        Vj = V[:, j]
        V = np.delete(V, j, 1)
        V = V - np.outer(Vj, V[int(Y[i]), :] / Vj[int(Y[i])])

        # QR decomposition, which is more numerically stable (and faster) than Gram
        # Schmidt
        if i > 0:
            V, r = np.linalg.qr(V)

    return Y
