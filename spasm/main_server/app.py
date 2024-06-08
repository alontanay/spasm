from typing import Any

import time
from threading import Thread, Lock, Event
from queue import Queue, Empty
import datetime

from Crypto.Random.random import sample

from spasm.common.protocol import Message, MessageType, reply
from spasm.common.network_components import DataServer
from spasm.common.atomic import safe_thread_target, ImpliedEvent
from spasm.common.defaults import REFRESH_DELAY
from spasm.common.graphics import LoggerGraphicInterface

from spasm.main_server.backend import MainServer
from spasm.main_server.loopback import LoopbackServer

class App:
    def __init__(self, main_address : tuple[str,int], loopback_address : tuple[str, int], data_servers : list[DataServer], base_data, public_key):
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
        
        self.gui = LoggerGraphicInterface(self.logger, 'Main Server', 'Main Server', public_key)
        self.gui.window.configure(bg='#333')
        self.gui.name.configure(background='#333',foreground='white')
        self.gui.public_key.configure(background='#333',foreground='white')
        self.gui.run(self.stop_event)
        
    def main_loop(self):
        try:
            while not self.stop_event.is_set():
                try:
                    msg = self.logger.get_nowait()
                    print(f'[{str(datetime.datetime.now())[:-7]}]',msg)
                except Empty:
                    time.sleep(REFRESH_DELAY)
                    pass
        except KeyboardInterrupt:
            self.stop_event.set()
        finally:
            print('Terminating...')
            self.loopback_server_thread.join()
            self.main_server_thread.join()
            try:
                while msg := self.logger.get_nowait():
                    print(f'[{str(datetime.datetime.now())[:-7]}]',msg)
            except Empty:
                pass
            print('Done.')
        