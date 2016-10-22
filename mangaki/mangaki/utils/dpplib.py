import numpy as np
import sys

def decompose_kernel(L):
  D, V = np.linalg.eigh(L)
  D = np.real(D)
  D[D<0] = 0
  idx = np.argsort(D)
  D = D[idx]
  V = np.real(V[:, idx])
  return D, V

def esym_poly(k, lam):
  N = lam.size
  E = np.zeros((k+1, N+1))
  E[0, :] = np.ones((1, N+1))
  for l in range(1, k+1):
    for n in range(1, N+1):
      E[l, n] = E[l, n-1] + lam[n-1]*E[l-1, n-1]

  return E

def E_Y(lam):
  return np.sum(lam/(1+lam))

def modifyLam(lam, c):
  return c*lam/(1+lam*(1-c))

def analyze_bDPP(lam):
  print("Ground set size:\t{0}".format(len(lam)))
  d = E_Y(lam)
  print("E[|Y|]:\t\t\t{0}".format(d))
  print("Maximum eigenvalue:\t{0}".format(np.max(lam)+1))
  cmax = 1/(np.max(lam)) + 1
  print("Maximum k:\t\t{0}".format(cmax*d))

def sample_EY(lam, V_full, k):
  d = E_Y(lam)
  cmax = 1/(np.max(lam)) + 1
  c = k/d
  if c>cmax:
    print("Warning: c>cmax. Continuing with regular DPP.")
    return sample(lam, V_full)

  L_C = modifyLam(lam, c)
  return sample(L_C, V_full)

def sample(lam, V_full):
  D = lam/(1+lam)
  v = np.random.rand(1, len(lam)) <= D
  k = np.sum(v)
  V = V_full[:, v.flatten()]
  Y = np.zeros((k, 1))

  for i in range(k-1, -1, -1):
    # Sample
    Pr = np.sum(V**2, axis=1)
    Pr = Pr/sum(Pr)
    C = np.cumsum(Pr)
    jj = np.argwhere(np.random.rand() <= C)[0]
    Y[i] = jj

    # Update V 
    if i > 0:
      j = np.argwhere(V[int(Y[i]), :])[0]
      Vj = V[:, j]
      V = np.delete(V, j, 1)
      V = V - np.outer(Vj, V[int(Y[i]), :]/Vj[int(Y[i])])

      # QR decomposition, which is more numerically stable (and faster) than Gram
      # Schmidt
      V, r = np.linalg.qr(V)

  return Y



def sample_k(k, lam, V_full):
  E = esym_poly(k, lam)
  J = []
  remaining = k-1
  i = lam.size-1

  while remaining>=0:
    marg = 0.0
    if i == remaining:
      marg = 1.0
    else:
      if E[remaining+1, i+1] == 0:
        i = i-1
        continue
      marg = lam[i]*E[remaining, i]/E[remaining+1, i+1]

    if np.random.rand() < marg:
      J.append(i)
      remaining = remaining-1
    
    i = i-1

  k = len(J)-1
  Y = np.zeros((len(J), 1))
  V = V_full[:, J]

  for i in range(k, -1, -1):
    # Sample
    Pr = np.sum(V**2, axis=1)
    Pr = Pr/sum(Pr)
    C = np.cumsum(Pr)
    jj = np.argwhere(np.random.rand() <= C)[0]
    Y[i] = jj

    # Update V 
    j = np.argwhere(V[int(Y[i]), :])[0]
    Vj = V[:, j]
    V = np.delete(V, j, 1)
    V = V - np.outer(Vj, V[int(Y[i]), :]/Vj[int(Y[i])])

    # QR decomposition, which is more numerically stable (and faster) than Gram
    # Schmidt
    if i > 0:
      V, r = np.linalg.qr(V)

  return Y

