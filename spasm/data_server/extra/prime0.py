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
    # print(isPrime(23023028871482552915685924579516880191402367541499539873166683696142280707361286654102736825247367720216107638817454197891699249918924178649416887658316713679375147366364733415007882414019115312769535724931740477982701464608008198242584217990576812377919698093322085306014399944193319017049515235085275069121390677747596320620551355571715089185101793811414316643742025585395342494035696610087256675798192876365672491289835536769971716073303545576519164745575928372396141681554024841283061554381068640260571741753871846793920010883930539558471825929026842856795830661368476845901809023286247616195064954257056607903433*2+1,1e-128))
    # b'\xc9\x1ef\xe0\x97<\x07E\x1f\x9b\xc4\r\xd6\x9d\xb5\x07\xb9<\xc6\xa6\x14~\xfb\x19U\xc6rTJ\x9c\xf5<\xf3\x91\xbb\xed\xfd&\x7f\x0c\xfc\x93\xf3za\x97#\xa5\xdcx\n\xeb@\x13\x03|\xa1\xddF\xbf\\\x84\x14c\x1e\xf8?Vdk\r\x11\x96\x1b\xd75~\xf9\xbd\x93h2\x16\x08\xaf\x12\x04\xf2M\xf0\x8dW\xa6m<\xc7\xcau\x1d\x1b\xb9X\xab\xdb\x06d\xbd\xc7\xd3;]G\x81btX\x1f\x1c\xb8y\xd3P\x01\xb4\xa9`\x82\x98\x86\x87\x10v\xa0\x0b\x92\xb9f-^\xa2\x1aU\xe7\xa0\xa0\xea[\xec\xc4\r\x85_\xf6M\xc3\xea\xe0\xa1@\xb2\xacx\x7f\x94\xc1\x12.^\t\x0c\xdd\xda\xcc\x1c\xa8Y\xf0\xb6W\xd2q\xd6u\xf1\r\xbej\xf2u\xbb5*\xb4xD\x0f\xbbs{\x88\xa6\xc3\xb2\xea\x9eO\xb1\xe8D\xfe\x9a\x91\xcfZ\xe1\xfa\n\xeb\xdb\x9e\xc8\xc6*\xa7TO\xb7{ut\x13\x0b}\xb5\xf6(z\xc6\x97\xe8\x84\xeb\xd5\x16\xc1\xda_\xbb\xad \x13\x01\x17\xa5`\xb6'
    cnt = 0
    while True:
        candidate = getPrime(N)
        if isPrime(candidate>>1):
            # raise Exception(str(candidate))
            print(candidate)
            exit(0)
        cnt += 1
        print('no',cnt)
    exit(0)
    counter_crypto = 0
    counter_my = 0
    cnt = 0
    while True:
        counter_crypto += time_func(getPrime,N)
        counter_my += time_func(gen_rand_prime,N)
        cnt += 1
        print('Crypto : ', counter_crypto / cnt)
        print('My Impl: ', counter_my / cnt)

# python3 prime0.py | python3 prime1.py | python3 prime2.py | python3 prime3.py
