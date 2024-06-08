import random
import time
from Crypto.Util.number import isPrime, getRandomNBitInteger

_SMALL_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233,
                239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293, 307, 311, 313, 317, 331, 337, 347, 349, 353, 359, 367, 373, 379, 383, 389, 397, 401, 409, 419, 421, 431, 433, 439, 443, 449, 457, 461, 463, 467, 479, 487, 491, 499, 503, 509, 521, 523, 541]

_MILLER_RABIN_ITERS = 64

def _is_prime_low(n):
    for p in _SMALL_PRIMES:
        if n % p == 0:
            return n == p
    return True


def _is_prime_high(n):
    e2 = 0
    odd = n-1
    while odd % 2 == 0:
        odd //= 2
        e2 += 1
    for _ in range(_MILLER_RABIN_ITERS):
        a = random.randint(2, n-2)
        x = pow(a, odd, n)
        for _ in range(e2):
            y = (x*x) % n
            if y == 1 and x != 1 and x != n - 1:  # nontrivial square root of 1 modulo n
                return False
            x = y
        if y != 1:
            return False
    return True

def _get_random_n_bit_int(n):
    return random.randint(1<<(n-1),(1<<n)-1)

def _gen_prime(bits):
    while True:
        n = _get_random_n_bit_int(bits)
        if n in _SMALL_PRIMES or (_is_prime_low(n) and _is_prime_high(n)):
            return n

def gen_sophie_germain_prime(bits):
    '''Uses PyCryptoDome's Util.number module'''
    while True:
        p = getRandomNBitInteger(bits-1)
        q = p*2+1
        if isPrime(p) and isPrime(q):
            return q

if __name__ == '__main__':
    assert gen_sophie_germain_prime(5) == 23
    assert gen_sophie_germain_prime(6) in [47,59]
    st = time.time()
    print('Sophie-Germain Prime:', gen_sophie_germain_prime(100))
    print('Time elapsed:', time.time()-st, 'seconds')