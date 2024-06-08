from spasm.main_server import App

from spasm_test import DATA_SERVERS, MAIN_SERVER, BASE_DATA

if __name__ == '__main__':
    app = App(MAIN_SERVER.BACKEND_ADDRESS,MAIN_SERVER.LOOPBACK_ADDRESS,DATA_SERVERS, BASE_DATA, MAIN_SERVER.PUBLIC_KEY)