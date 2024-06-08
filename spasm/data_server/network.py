from __future__ import annotations

from typing import Optional, Union, Callable, Any, overload
from dataclasses import dataclass
from enum import Enum

import traceback
import errno
import socket
from threading import Thread, Lock, Event
from queue import Queue, Empty
import time

from Crypto.Hash import SHA384

from spasm.common.error import DataUnavailableError, ProtocolViolation
from spasm.common.protocol import ByteBuffer, Message, MessageType
from spasm.common.atomic import safe_thread_target, ImpliedEvent
from spasm.common.diffie_hellman import DiffieHellmanState
from spasm.common.network_components import DataServer
from spasm.common.security import AsymmetricKey
from spasm.common.defaults import REFRESH_DELAY

from spasm.data_server.data import DataComponent

TIMEOUT = 4

class ServerComponent:
    def __init__(self, address : tuple[str,int], logger : Queue, database : DataComponent, security_key : AsymmetricKey, data_servers : list[DataServer], this_data_server : DataServer):
        self.address = address
        self.logger = logger
        self.database = database
        self.security_key = security_key
        self.known_data_servers = data_servers
        self.this_data_server = this_data_server
        
        self.key_exchange_component : DiffieHellmanState = None
        
        self.key_queue = Queue()
        self.database_output = Queue()

    def reply_ok(self, request : Message, data = None):
        self.main_connection.send(request.generate_reply(True,data).to_bytes())

    def handle_request(self, request : Message):
        self.logger.put(f'[NETWORK] received message from main: type `{\
            request.type}`, id `{request.id}`, sid `{request.session_id}`.')
        match request.type:
            case MessageType.KEY_EXCHANGE_INIT:
                data_server_ids : list[str] = request.data
                data_servers : list[DataServer] = []
                for data_server in self.known_data_servers:
                    if data_server.id in data_server_ids:
                        data_servers.append(data_server)
                self.active_data_servers = data_servers
                N = len(data_servers)
                this_index = data_servers.index(self.this_data_server)
                self.prev_data_server = data_servers[(this_index + N - 1) % N]
                self.next_data_server = data_servers[(this_index + 1) % N]
                self.key_exchange_N = N
                self.key_exchange_component = DiffieHellmanState(N)
                self.logger.put('[KEY EXCHANGE] Initialized key exchange component.')
                self.reply_ok(request)
            case MessageType.KEY_EXCHANGE_START:
                with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
                    sock.setblocking(False)

                    try:
                        sock.connect(self.next_data_server.address)
                    except OSError as e:
                        if e.errno != errno.EINPROGRESS:
                            raise
                    
                    timed_stop = ImpliedEvent(self.stop_event,TIMEOUT)
                    while not timed_stop.is_set():
                        try:
                            sock.recv(1)
                            break
                        except BlockingIOError as e:
                            time.sleep(REFRESH_DELAY)
                            pass
                    if timed_stop.is_set():
                        raise Exception(f'Could not connect to data server at {self.next_data_server.address}.')
                    
                    self.logger.put(f'[NETWORK] Connected to data server at {self.next_data_server.address}.')
                    for step in range(self.key_exchange_N-1):
                        sock.send(Message(MessageType.KEY_EXCHANGE_STEP,data=self.key_exchange_component.public_key(),session_id=request.session_id).to_bytes())
                        while not self.stop_event.is_set():
                            try:
                                self.key_exchange_component.transform_intermediate_key(self.key_queue.get())
                                break
                            except Empty:
                                time.sleep(REFRESH_DELAY)
                                pass
                self.shared_key = self.key_exchange_component.result()
                self.shared_key_proof = SHA384.new(self.shared_key).hexdigest()
                self.reply_ok(request, self.shared_key_proof)
                self.logger.put('[KEY EXCHANGE] Key exchange done. closing connections.')
            case MessageType.DATA_REQUEST:
                ids = request.data
                result = self.database._read(ids, self.shared_key)
                self.reply_ok(request, result)
            case _:
                raise NotImplementedError

    def handle_main_connection(self):
        self.logger.put(f'[SERVER] Start of connection with main server at {self.main_address}.')
        reader = ByteBuffer()
        self.main_connection.setblocking(False)
        self.main_connection.send(b'$')
        while not self.stop_event.is_set():
            time.sleep(REFRESH_DELAY)
            try:
                reader.append(self.main_connection.recv(2048))
            except BlockingIOError:
                pass
            except DataUnavailableError:
                break
            else:
                reader.save()
                try:
                    message = Message.from_bytes(buff=reader)
                    self.handle_request(message)
                except DataUnavailableError:
                    reader.restore()
            
        self.logger.put(f'[SERVER] End of connection with main at {self.main_address}.')
        self.stop_event.set()
    
    def handle_backward_connection(self, conn : socket.socket, addr):
        self.logger.put(f'[SERVER] Start of connection with data server at {addr}.')
        reader = ByteBuffer()
        conn.setblocking(False)
        conn.send(b'$')
        while not self.stop_event.is_set():
            time.sleep(REFRESH_DELAY)
            try:
                reader.append(conn.recv(2048))
            except BlockingIOError:
                pass
            except DataUnavailableError:
                break
            else:
                reader.save()
                try:
                    message : Message = Message.from_bytes(buff=reader)
                    self.logger.put(f'[NETWORK] received message from main: type `{\
                        message.type}`, id `{message.id}`, sid `{message.session_id}`.')
                    self.key_queue.put(message.data)
                except DataUnavailableError:
                    reader.restore()
        self.logger.put(f'[SERVER] End of connection with {addr}.')

    def run(self, stop_event: Event):
        self.stop_event = stop_event
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                server.bind(self.address)
                server.listen(1)
                server.setblocking(False)

                self.logger.put(f'[SERVER] Started Server. Listening on {\
                    self.address}.')

                while not stop_event.is_set():
                    try:
                        self.main_connection, self.main_address = server.accept()
                        break
                    except BlockingIOError:
                        time.sleep(REFRESH_DELAY)
                        pass
                
                if stop_event.is_set():
                    return
                
                Thread(target=safe_thread_target(self.logger,self.stop_event,self.handle_main_connection)).start()
                
                while not stop_event.is_set():
                    try:
                        conn, addr = server.accept()
                        self.handle_backward_connection(conn, addr)
                    except IOError as e:
                        time.sleep(REFRESH_DELAY)
        except Exception as e:
            self.logger.put(f'[ERROR-NETWORK] {e}')
            self.stop_event.set()
        finally:
            self.logger.put(f'[SERVER] Closed Server.')
