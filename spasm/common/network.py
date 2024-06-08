from typing import Any, Iterable

import socket

from queue import Queue, Empty
from threading import Lock, Event

from spasm.common.atomic import ImpliedEvent
from spasm.common.protocol import Message, MessageType
from spasm.common.network_components import DataServer, MAIN_BACKEND_NETWORK_COMPONENT, MAIN_LOOPBACK_NETWORK_COMPONENT

# def who_is_at_address(address : tuple[str,int]):
#     if address == MAIN_SERVER.LOOPBACK_ADDRESS:
#         return MAIN_LOOPBACK_NETWORK_COMPONENT
#     elif address == MAIN_SERVER.BACKEND_ADDRESS:
#         return MAIN_BACKEND_NETWORK_COMPONENT
#     for data_server in DATA_SERVERS.values():
#         if address == data_server.address:
#             return data_server
#     return None

class NetworkComponent:
    pass
class Connection:
    _sock : socket.socket
    id : int
    def __init__(self, sock : socket.socket, address : tuple[str,int], stop_event : Event):
        self._sock = sock
        self.address = address
        self._buf = b''
        self.stop_event = ImpliedEvent(stop_event)
        self._thread = Thread(target=self.run,args=())
    
    def __enter__(self):
        try:
            self._sock
            return self
        except BlockingIOError:
            self._sock.close()
    
    def __exit__(self):
        self._sock.close()
    
    def receive_exact(self, exact_size : int):
        '''Not thread-safe.'''
        # ! TODO
        while len(self.buf) < exact_size:
            pass
    
    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            
    

def is_preferred_connection(connection : Connection | None, new_alternative : Connection):
    return connection is not None and (connection.is_active() or connection.id > new_alternative.id)


def make_connection(recipient : NetworkComponent, message_queue : Queue, stop_event : Event):
    connection = Connection()

def send_message(conn: socket.socket, *args, **kwargs):
    conn.send(Message(*args, **kwargs).to_bytes())


def receive_message(conn: socket.socket, timeout: float | None = None) -> Message:
    return Message.from_bytes(buff=conn, timeout=timeout)


def reply(conn: socket.socket, request: Message, successful=True, data=None):
    conn.send(Message(MessageType.RESPONSE_OK if successful else MessageType.RESPONSE_FAILED,
              data, request.id).to_bytes())


def reply_ok(conn: socket.socket, request: Message, data=None):
    reply(conn, request, True, data)


def reply_failed(conn: socket.socket, request: Message, data=None):
    reply(conn, request, False, data)