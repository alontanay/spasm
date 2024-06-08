from typing import TypeVar, Optional, Any

from threading import Thread, Event, Lock
from queue import Queue
import socket
import time

from spasm.common.network_components import NetworkComponent, DataServer
from spasm.common.protocol import Message, ProtocolViolation
from spasm.common.network import Connection, make_connection, is_preferred_connection
from spasm.common.sessions import CommunicationSession
from spasm.common.atomic import AtomicDict, LockedDictContext

CONNECTION_UPDATE_DELAY = 1.0

class Server:

    address: tuple[str, int]
    logger: Queue

    sessions: AtomicDict[int, CommunicationSession]
    outgoing_messages : AtomicDict[NetworkComponent, Queue]
    connections : AtomicDict[NetworkComponent, Connection]

    def __init__(self, address: tuple[str, int], logger: Queue):
        self.address = address
        self.logger = logger
        
        self.sessions = AtomicDict()
        self.outgoing_messages = AtomicDict()
        self.connections = AtomicDict()
    
    def get_message_queue(self, recipient : NetworkComponent):
        with self.outgoing_messages as outgoing_messages:
            if (res := outgoing_messages.get(recipient)) is None:
                outgoing_messages[recipient] = (res := Queue())
                return res
            return res
    
    def connect(self, recipient : NetworkComponent):
        with self.connections as connections:
            if connections.get(recipient) is None:
                connections[recipient] = make_connection(recipient, self.get_message_queue(recipient), self.stop_event)

    def update_connections(self):
        with self.outgoing_messages as outgoing_messages:
            with self.connections as connections:
                for recipient, message_queue in outgoing_messages.items():
                    if message_queue.qsize() and connections.get(recipient) is None:
                        connections[recipient] = make_connection(recipient, message_queue, self.stop_event)
    
    def send_message(self, recipient : NetworkComponent, message : Message):
        self.connect(recipient)
        with self.outgoing_messages:
            self.outgoing_messages[recipient].put(message)
    
    def reply_ok(self, sender : NetworkComponent, request : Message, data : Optional[Any]):
        self.send_message(sender, request.generate_reply(True,data))
    
    def reply_failed(self, sender : NetworkComponent, request : Message, data : Optional[Any]):
        self.send_message(sender, request.generate_reply(False,data))

    def get_session(self, session_id: int):
        '''Thread-safe'''
        with self.sessions:
            return self.sessions.get(session_id)

    def kill_session(self, session_id: int):
        '''Thread-safe'''
        with self.sessions:
            old_session = self.sessions.pop(session_id, None)
            if session_existed := (old_session is not None):
                old_session.kill()
            return session_existed

    def new_session(self, session_id : int):
        '''Thread-safe'''
        with self.sessions:
            old_session = self.sessions.pop(session_id, None)
            if old_session_existed := (old_session is not None):
                old_session.kill()

            self.sessions[session_id] = CommunicationSession(
                session_id, self.impl_handle_session)
            
            return old_session_existed

    def forward_to_session(self, sender : NetworkComponent, message : Message):
        '''Forwards a message with positive `session_id` to its corresponding session's `incoming_queue`'''
        session = self.get_session(message.session_id)
        if session is None:
            raise ProtocolViolation(f'No session with id {message.id}.')
        session.incoming_requests.put((sender,message))
        
    def impl_handle_session(self, session: CommunicationSession):
        raise NotImplementedError
    
    def impl_handle_connection(self, in_queue: Queue, out_queue: Queue):
        '''Can call `kill_session(id)`, `new_session(id)`, `forward_to_session(sender, message)`'''
        raise NotImplementedError

    def call_connection_handler(self):
        try:
            self.handle_connection_impl()
        except ProtocolViolation as e:
            self.logger.put('[ERROR] ' + str(e))

    def _handle_connection(self, sock: socket.socket, addr: tuple[str, int]):
        self.logger.put(f'[SERVER] Start of connection with {addr}.')
        try:
            conn = Connection(sock, addr, self.stop_event)
            recipient = conn.who
            with self.connections as connections:
                old_connection = connections.get(recipient)
                if old_connection is not None and is_preferred_connection(old_connection, conn):
                    conn.reject()
                    raise ProtocolViolation(f'There\'s already an established connection with {addr}')
                old_connection.close()
                conn.accept()
                connections[recipient] = conn

                
            self.handle_connection_impl(conn)
        except ProtocolViolation as e:
            self.logger.put('[ERROR] ' + str(e))
        finally:
            if conn:
                conn.close()
            self.logger.put(f'[SERVER] End of connection with {addr}.')

    def run(self, stop_event: Event):
        self.stop_event = stop_event
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                server.bind(self.address)
                server.listen()
                server.setblocking(False)

                self.logger.put(f'[SERVER] Started Server. Listening on {\
                    self.address}.')

                last_connection_update = time.thread_time()
                while not stop_event.is_set():
                    current_time = time.thread_time()
                    if current_time - last_connection_update > CONNECTION_UPDATE_DELAY:
                        self.update_connections()
                        last_connection_update = current_time

                    try:
                        sock, addr = server.accept()
                        Thread(target=safe_thread_target(self.logger,self.stop_event,self._handle_connection), args=(sock,addr)).start()
                    except BlockingIOError:
                        time.sleep(REFRESH_DELAY)
                        pass
        finally:
            self.logger.put(f'[SERVER] Closed Server.')