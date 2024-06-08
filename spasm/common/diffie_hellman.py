from typing import Callable
from Crypto.Random.random import getrandbits
from Crypto.Hash import SHA384

class KeyExchangeError(Exception):
    pass

# # 2048
# MODULUS = 25989389641921276647108510151280079678797779144836196678738525895929416263022550876704444832025837795493964669333377930118523898206656955058983203999498342596083215877877838559333598787247530959420327683672380646381683597471160657471474874124135220792527850205849454190229036918761851880597052625959860408785453007734034923111779693239173561348322375901528699826577758924652586347773854115711399677533793441220291768623556897313293904862661246045536938603957615661811385514189118178632617389286336457140859571461202619183978269351397009490126797544115723542585859919089998637796439828191759310660031783405445032995787

# 4096
MODULUS = 862500856745426373114905162935473402137625040803523406799555364772769246033292946853887578464421747330798806131512518480050504893357640514819520008444284556127041593924110354910763041900773281223467875394392855532672747640777769280693068249012345540823579103254335760795027611377618988826087358312883174198760444560820041925044811524498487018283184311853786255067619308136974035910760234297599569435464678638142954501867016044395080260054823955771499849758482460702350713828784210461378241478714025959995954396232840322224435876656171282718011485549295407254100505479379605684920553504097863256394967179527118663973175060842344968008437866664934343323383690062123326285498015583093187558364772362626627501100148898374549760841234079491164193149205302703762803481685117023145717824002247291374124750762840961849708252395074088836254301831938085567663966510643194786214780862406544319057317885250058713333255529656022074998988267540105515386811757060615910180688523728486741279061151919449978516761844187239013393229187182159947756685267361291181063994011689211630313046273627114623421292905195402496538142692725713072606938108366022507229123664302120960935808408829593717496862145056334670681878358709680217679538759812378931657901887

MOD_BIT_LENGTH = MODULUS.bit_length()
MOD_BYTE_LENGTH = (MOD_BIT_LENGTH + 7) // 8

GENERATOR = 4

assert pow(GENERATOR, MODULUS//2, MODULUS) == 1

class DiffieHellmanState:
    def __init__(self, n : int):
        self._n = n
        self._step = 0
        self._private_key = getrandbits(MOD_BIT_LENGTH)
        self.transform_intermediate_key(GENERATOR)
    
    def transform_intermediate_key(self, key : int) -> int:
        if self._step >= self._n:
            raise KeyExchangeError(f'Tried performing more than N - 1 ({self._n-1}) steps.')
        self._latest_key = pow(key, self._private_key, MODULUS)
        self._step += 1
        return self._latest_key
    
    def public_key(self):
        if self._step >= self._n:
            raise KeyExchangeError(f'Tried accessing final key as public. use result() instead.')
        return self._latest_key
    
    def result(self):
        if self._step != self._n:
            return None
        
        secret = self._latest_key.to_bytes((MOD_BIT_LENGTH+7)//8,'little')
        return SHA384.new(secret).digest()

if __name__ == '__main__':
    print('asymmetric.py main')
    # DH example ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    N = 2
    parties = [DiffieHellmanState(N) for _ in range(N)]
    
    for it in range(N-1):
        first_key = parties[0].public_key()
        for i in range(0,N-1):
            parties[i].transform_intermediate_key(parties[i+1].public_key())
        parties[N-1].transform_intermediate_key(first_key)
    
    exp_sum = 1
    last_party = parties[-1]
    for party in parties:
        exp_sum *= party._private_key
        assert(last_party.result() == party.result())
        last_party = party
    assert(SHA384.new(pow(GENERATOR,exp_sum,MODULUS).to_bytes((MOD_BIT_LENGTH+7)//8,'little')).digest() == last_party.result())
