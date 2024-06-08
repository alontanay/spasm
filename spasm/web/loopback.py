from queue import Queue
from threading import Lock, Event
import socket
import time

from spasm.common.atomic import ImpliedEvent
from spasm.common.protocol import Message, MessageType
from spasm.common.queries import ConditionsType, conditional_to_struct, conditions_from_user_text

class WebLoopback:
    def __init__(self):
        self._initialized = False
    def is_initialized(self):
        return self._initialized
    
    def init(self, loopback_address : tuple[str,int]):
        self.loopback_address = loopback_address
        self.conn_lock = Lock()
        self.conn_lock.acquire()
        
    def run(self, stop_event : Event):
        self.stop_event = stop_event
        
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as self.sock:
            self.sock.connect(self.loopback_address)
            print('Connected')
            self._initialized = True
            self.conn_lock.release()
            stop_event.wait()

        
            
    def data_request(self, condition_text : str):
        if self.stop_event.is_set():
            raise Exception("Stopped accepting queries.")
        try:
            conditions = conditions_from_user_text(condition_text)
            with self.conn_lock:
                self.sock.send(Message(MessageType.USER_DATA_REQUEST,conditional_to_struct(conditions)).to_bytes())
                return Message.from_bytes(buff=self.sock,stop_event=self.stop_event).data
        except Exception as e:
            print('Backend error!')
            print(e)
            self.stop_event.set()
            raise e