from dataclasses import dataclass

from spasm.common.network_components import DataServer

BASE_DATA = {
    '123456789': {'age': 18, 'sex': 'M'},
    '000000000': {'age': 77, 'sex': 'F'},
    '473852958': {'age': 30, 'sex': 'F'},
    '234899843': {'age': 56, 'sex': 'M'},
    '232837878': {'age': 83, 'sex': 'M'},
    '948943859': {'age': 28, 'sex': 'F'},
    '872874828': {'age': 40, 'sex': 'F'},
    '123827389': {'age': 44, 'sex': 'F'}
}

DATA_IDS = [key for key in BASE_DATA]

DATA_SERVERS = [
    DataServer('rZ6N6hqv', ('localhost', 9000), 'GUIAVA', {'name': 'Maccabbage Healthcare Services', 'location': 'Everywhere'}),
    DataServer('Boc8_pQ5', ('localhost', 9001), 'DURIAN', {'name': 'Kiwi International Hospital.', 'location': 'Online'}),
    DataServer('uyuJpfBd', ('localhost', 9002), 'GAMBA', {'name': 'Gamba-le Insurance', 'location': 'Wherever\'s convinient.'}),
]

class MAIN_SERVER:
    LOOPBACK_ADDRESS = ('localhost', 5550)
    BACKEND_ADDRESS = ('localhost', 5551)
    PUBLIC_KEY = 'BANANA'