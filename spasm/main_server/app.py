from typing import Any

from threading import Thread, Event
from queue import Queue, Empty

from Crypto.Random.random import sample

from spasm.common.protocol import Message
from spasm.common.security import AsymmetricKey
from spasm.common.network_components import DataServer
from spasm.common.atomic import safe_thread_target, ImpliedEvent
from spasm.common.graphics import LoggerGraphicInterface, time_now

from spasm.main_server.backend import MainServer
from spasm.main_server.loopback import LoopbackServer

class App:
    def __init__(self, main_address : tuple[str,int], loopback_address : tuple[str, int], data_servers : list[DataServer], base_data, key : AsymmetricKey):
        self.logger : Queue[str] = Queue()
        self.stop_event = Event()
        self.sub_stop_event = ImpliedEvent(self.stop_event)
        
        self.user_query_queue : Queue[tuple[Message,Any]] = Queue()
        self.query_result_queue : Queue[tuple[Message,Any]] = Queue()
        
        self.main_server = MainServer(self.logger, main_address, data_servers, base_data, self.user_query_queue, self.query_result_queue)
        self.loopback_server = LoopbackServer(self.logger, loopback_address, data_servers, self.user_query_queue, self.query_result_queue)
        
        self.main_server_thread = Thread(target=safe_thread_target(self.logger,self.sub_stop_event,self.main_server.run),args=(self.sub_stop_event,))
        self.loopback_server_thread = Thread(target=safe_thread_target(self.logger,self.sub_stop_event,self.loopback_server.run),args=(self.sub_stop_event,))
        
        self.main_server_thread.start()
        self.loopback_server_thread.start()
        
        self.gui = LoggerGraphicInterface(self.logger, 'Main Server', 'Main Server', key)
        self.gui.window.configure(bg='#333')
        self.gui.name.configure(background='#333',foreground='white')
        self.gui.public_key.configure(background='#333',foreground='white')
        
        try:
            self.gui.run(self.stop_event)
        except KeyboardInterrupt:
            print('KeyBoardInterrupt')
        finally:
            self.stop_event.set()
        self.main_server_thread.join()
        self.loopback_server_thread.join()
        print('Terminating...')
        try:
            while msg := self.logger.get_nowait():
                print(f'[{time_now()}]',msg)
        except Empty:
            pass
        print('Done.')
        