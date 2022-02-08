from collections import defaultdict
from random import randint
import numpy as np


# PRIME = 7919
PRIME = 999331
# PRIME = 1645333507


# From TryAlgo
def expmod(a, b, q=PRIME):
    """Compute (a pow b) % q, alternative shorter implementation
    :param int a b: non negative
    :param int q: positive
    :complexity: O(log b)
    """
    assert a >= 0 and b >= 0 and q >= 1
    result = 1
    while b:
        if b % 2 == 1:
            result = (result * a) % q
        a = (a * a) % q
        b >>= 1
    return result


def bezout(a, b):
    """Bézout coefficients for a and b
    :param a,b: non-negative integers
    :complexity: O(log a + log b)
    """
    if b == 0:
        return (1, 0)
    u, v = bezout(b, a % b)
    return (v, u - (a // b) * v)


def inv(a, p=PRIME):
    """Inverse of a in :math:`{mathbb Z}_p`
    :param a,p: non-negative integers
    :complexity: O(log a + log p)
    """
    return bezout(a, p)[0] % p


class HomomorphicEncryption:
    def __init__(self, user_ids, quantize_round=0, MAX_VALUE=10):
        self.user_ids = user_ids
        self.quantize_round = quantize_round
        self.g = randint(2, PRIME - 1)
        self._keygen()
        self._shares = {}
        self._encode(MAX_VALUE)

    def _keygen(self):
        self._sk = {user: randint(2, PRIME - 2) for user in self.user_ids}
        self._pk = {user: expmod(self.g, self._sk[user]) for user in self.user_ids}

    def _encode(self, MAX_VALUE):
        self.encode = {x: expmod(self.g, x) for x in range(0, MAX_VALUE + 1)}
        for x in range(1, MAX_VALUE + 1):
            self.encode[-x] = inv(self.encode[x])
        self.decode = {v: k for k, v in self.encode.items()}
        assert len(self.encode) == len(self.decode)  # Otherwise PRIME is too small

    def encrypt(self, user_id, message: int):
        r = randint(0, PRIME)
        c1 = expmod(self.g, r)
        return c1, (self.encode[message] * expmod(self._pk[user_id], r)) % PRIME

    def encrypt_embeddings(self, user_id, parameters):
        mean, feat = parameters
        feat = np.array(feat)
        if self.quantize_round:
            mean = int((10 ** self.quantize_round) * mean.round(self.quantize_round))
            feat = ((10 ** self.quantize_round) * feat.round(self.quantize_round)).astype(int)
        encrypted = []
        self._shares[user_id] = np.zeros(1 + len(feat), dtype=int)
        for dim, value in enumerate([mean] + feat.tolist()):
            c1, c2 = self.encrypt(user_id, value)
            self._shares[user_id][dim] = expmod(c1, self._sk[user_id])
            encrypted.append(c2)
        return np.array(encrypted)

    def combine_embeddings(self, encrypted_embeddings):
        combined = np.ones_like(encrypted_embeddings[0])
        for encrypted_embedding in encrypted_embeddings:
            combined *= encrypted_embedding
            combined %= PRIME
        self._combined_shares = np.ones_like(encrypted_embeddings[0])
        for user_id in self.user_ids:
            self._combined_shares *= self._shares[user_id]
            self._combined_shares %= PRIME
        return combined

    def decrypt_embeddings(self, encrypted_embeddings):
        combined = self.combine_embeddings(encrypted_embeddings)
        inversed_shares = [inv(value) for value in self._combined_shares]
        decrypted = (combined * inversed_shares) % PRIME
        decoded = np.array([self.decode[value] for value in decrypted], dtype=float)
        if self.quantize_round:
            decoded /= 10 ** self.quantize_round
        return decoded[0], decoded[1:]  # Mean, feat
