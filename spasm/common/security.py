from typing import Optional

from dataclasses import dataclass

from Crypto.PublicKey import ECC

class PrivateKey:
    _key : ECC.EccKey
    def __init__(self, key : Optional[ECC.EccKey] = None):
        self._key = ECC.generate(curve='p256') if key is None else key
        
    def public_key(self):
        return self._key.public_key()

class PublicKey:
    _key : ECC.EccKey
    def __init__(self, private_key : ECC.EccKey):
        self._key = private_key

class AsymmetricKey:
    def __init__(self, private_key : Optional[PrivateKey] = None):
        self._private_key = PrivateKey() if private_key is None else private_key
        self._public_key = self._private_key.public_key()
    
    def public_key(self):
        return self._public_key
    