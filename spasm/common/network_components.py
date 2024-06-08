from dataclasses import dataclass

from spasm.common.security import PublicKey

class NetworkComponent:
    pass

@dataclass(eq=False, frozen=True)
class DataServer(NetworkComponent):
    id : str
    address : tuple[str,int]
    public_key : PublicKey
    information : dict[str]

MAIN_LOOPBACK_NETWORK_COMPONENT = NetworkComponent()
MAIN_BACKEND_NETWORK_COMPONENT = NetworkComponent()