from __future__ import annotations
from typing import Optional, Union, Callable, Any, overload

import traceback

from dataclasses import dataclass
from enum import Enum

import errno
import socket
from threading import Thread, Lock, Event
from queue import Queue, Empty
import time

from Crypto.Hash import SHA384

from spasm.common.error import DataUnavailableError, ProtocolViolation
from spasm.common.protocol import ByteBuffer, Message, MessageType
from spasm.common.atomic import Promise
from spasm.common.diffie_hellman import DiffieHellmanState
from spasm.common.network_components import DataServer
from spasm.common.security import AsymmetricKey
from spasm.common.defaults import REFRESH_DELAY


class LoopbackServer:
    def __init__(self, logger : Queue, address : tuple[str,int], data_servers : list[DataServer], user_requests : Queue, user_results : Queue):
        self.address = address
        self.logger = logger
        self.data_servers = data_servers
        
        self.user_requests = user_requests
        self.user_results = user_results

    def reply_ok(self, request : Message, data = None):
        self.main_connection.send(request.generate_reply(True,data).to_bytes())

    def handle_request(self, request : Message):
        self.logger.put(f'[NETWORK-LOOPBACK] received message from web: type `{\
            request.type}`, id `{request.id}`, sid `{request.session_id}`.')
        match request.type:
            case MessageType.PING:
                self.reply_ok(request)
            case MessageType.USER_DATA_REQUEST:
                self.user_requests.put((request, request.data))
            case _:
                raise NotImplementedError

    def handle_main_connection(self):
        self.logger.put(f'[NETWORK-LOOPBACK] Start of connection with web server at {self.web_address}.')
        reader = ByteBuffer()
        self.main_connection.setblocking(False)
        while not self.stop_event.is_set():
            time.sleep(REFRESH_DELAY)
            try:
                reader.append(self.main_connection.recv(2048))
            except BlockingIOError:
                pass
            except DataUnavailableError:
                break
            except IOError as e:
                self.logger.put(f'[ERROR-LOOPBACK] {e}')
                break
            else:
                reader.save()
                try:
                    message = Message.from_bytes(buff=reader)
                    self.handle_request(message)
                except DataUnavailableError:
                    reader.restore()
            
            try:
                message,reply = self.user_results.get_nowait()
                self.logger.put(f'[LOOPBACK] Returning result: `{message.id}`, data: `{reply}`.')
                self.reply_ok(message, reply)
            except Empty:
                pass
        
        self.logger.put(f'[NETWORK-LOOPBACK] End of connection with web {self.web_address}.')
        
    def run(self, stop_event: Event):
        self.stop_event = stop_event
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                server.bind(self.address)
                server.listen(1)
                server.setblocking(False)
                self.logger.put(f'[NETWORK-LOOPBACK] Started Loopback Server. Listening on {self.address}.')

                while not stop_event.is_set():
                    try:
                        self.main_connection, self.web_address = server.accept()
                        with self.main_connection:
                            self.handle_main_connection()
                    except BlockingIOError:
                        time.sleep(REFRESH_DELAY)
                        pass
        except Exception as e:
            self.logger.put(traceback.format_exc())
            self.logger.put(f'[ERROR-LOOPBACK] {e}')
            self.stop_event.set()
        finally:
            self.logger.put('[NETWORK-LOOPBACK] Closed Loopback Server.')
