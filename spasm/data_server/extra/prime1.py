import random
from Crypto.Util.number import getPrime, isPrime
import time

SMALL_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233,
                239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293, 307, 311, 313, 317, 331, 337, 347, 349, 353, 359, 367, 373, 379, 383, 389, 397, 401, 409, 419, 421, 431, 433, 439, 443, 449, 457, 461, 463, 467, 479, 487, 491, 499, 503, 509, 521, 523, 541]

MILLER_RABIN_ITERS = 64

def is_prime_low(n):
    for p in SMALL_PRIMES:
        if n % p == 0:
            return False
    return True


def is_prime_high(n):
    e2 = 0
    odd = n-1
    while odd % 2 == 0:
        odd //= 2
        e2 += 1
    for _ in range(MILLER_RABIN_ITERS):
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


def gen_rand_prime(bits):
    st = time.time()
    it = 0
    while True:
        n = random.randint(1 << (bits-2), (1 << (bits-1)) - 1) * 2 + 1
        # print(it)
        if n in SMALL_PRIMES or (is_prime_low(n) and is_prime_high(n)):
            en = time.time()
            print('done after',it,'iterations.')
            print(en-st)
            return n
        # it += 1

def time_func(func, *args, **kwargs):
    st = time.time()
    func(*args, **kwargs)
    en = time.time()
    return en-st

if __name__ == '__main__':
    N = 4096
    while True:
        candidate = getPrime(N)
        if isPrime(candidate>>1):
            # raise Exception(str(candidate))
            print(candidate)
        print('no')