from spasm.web import app, web_backend, data_servers
from threading import Thread, Event

from spasm_test import MAIN_SERVER, DATA_SERVERS

if __name__ == '__main__':
    stop_event = Event()
    data_servers.extend(DATA_SERVERS)
    web_backend.init(MAIN_SERVER.LOOPBACK_ADDRESS)
    Thread(target=web_backend.run,args=(stop_event,)).start()
    app.run(port=5000,debug=True,use_reloader=False)
    stop_event.set()