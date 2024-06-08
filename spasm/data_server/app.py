from __future__ import annotations

from queue import Queue, Empty
from threading import Thread, Event

from spasm.common.network_components import DataServer
from spasm.common.security import AsymmetricKey
from spasm.common.atomic import safe_thread_target, ImpliedEvent
from spasm.common.graphics import LoggerGraphicInterface, time_now

class App:
    def __init__(self, address: tuple[str, int], database: Database, key : AsymmetricKey, data_servers : list[DataServer], this_data_server : DataServer):
        self.address = address

        self.logger = Queue()
        
        self.outside_representation = this_data_server

        self.stop_event = Event()
        self.sub_stop_event = ImpliedEvent(self.stop_event)

        self.database = DataComponent(database, self.logger)
        self.server = ServerComponent(address, self.logger, self.database, key, data_servers, this_data_server)
        self.gui = LoggerGraphicInterface(self.logger, 'Data Server', f'Data Server of "{this_data_server.information["name"]}"', this_data_server.public_key)

        self.database_thread = Thread(
            target=safe_thread_target(self.logger,self.sub_stop_event,self.database.run), args=(self.sub_stop_event,))
        self.database_thread.start()

        self.server_thread = Thread(
            target=safe_thread_target(self.logger,self.sub_stop_event,self.server.run), args=(self.sub_stop_event,))
        self.server_thread.start()
        
        try:
            self.gui.run(self.stop_event)
        except KeyboardInterrupt:
            print('KeyBoardInterrupt')
        finally:
            self.stop_event.set()
        self.database_thread.join()
        self.server_thread.join()
        print('Terminating...')
        try:
            while msg := self.logger.get_nowait():
                print(f'[{time_now()}]',msg)
        except Empty:
            pass
        print('Done.')

    def __repr__(self) -> str:
        return f'App[at address {self.address}]'

from spasm.data_server.data import DataComponent, Database
from spasm.data_server.network import ServerComponent
