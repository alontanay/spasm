
import sys
print(sys.argv)


from spasm.common.security import AsymmetricKey   
 
from spasm.data_server import App, Database

from spasm_test import DATA_SERVERS

import copy
import json

class JsonFileDatabase(Database):
    # def write_disk(self):
    #     with open(self.file_location, 'w') as f:
    #         json.dump(self.data, f)

    def read_disk(self):
        with open(self.file_location, 'r') as f:
            self.data : dict = json.load(f)

    def __init__(self, location : str):
        self.file_location = location
        self.read_disk()

    def get(self, id):
        return copy.deepcopy(self.data.get(id))

    # def set(self, id, data):
    #     self.data[id] = copy.deepcopy(data)
    #     self.write_disk()

    # def clear(self):
    #     self.data = {}
    #     self.write_disk()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Must provide exactly one parameter: index of Data Server to run.')
        exit(0)
    idx = int(sys.argv[1])
    data_server = DATA_SERVERS[idx]
    id = data_server.id
    security_key = AsymmetricKey()
    app = App(data_server.address,
                    JsonFileDatabase(f'mem/data_server{idx}.json'), security_key, DATA_SERVERS, data_server)