from typing import Optional, Any

import errno

from enum import Enum
from dataclasses import dataclass

from queue import Queue, Empty
from threading import Thread, Event, Lock
import time
import socket

from Crypto.Random.random import sample


from spasm.common.network_components import DataServer
from spasm.common.atomic import AtomicCounter, AtomicDict, ImpliedEvent, safe_thread_target
from spasm.common.protocol import Message, MessageType, ByteBuffer, DataUnavailableError
from spasm.common.queries import Condition, ConditionsType, BoundType, filter_ids, conditional_from_struct
from spasm.common.diffie_hellman import KeyExchangeError
from spasm.common.defaults import REFRESH_DELAY

class BadDataServerError(Exception):
    pass


TIMEOUT = 4

ID_SAMPLE_SIZE = 3
STUDY_GROUP_MINIMAL_SIZE = 4

class MainServer:
    def __init__(self, logger: Queue, address: tuple[str, int], data_servers: list[DataServer], base_data: dict, user_query_queue: Queue, query_result_queue: Queue):
        self.logger = logger
        self.address = address
        self.data_servers = data_servers
        self.data_server_ids = [data_server.id for data_server in data_servers]

        self.connections: dict[DataServer, socket.socket] = {}
        # self.requests : AtomicDict[DataServer,Queue[Message,Queue]] = AtomicDict([(data_server,Queue()) for data_server in data_servers])
        # self.responses : AtomicDict[DataServer,Queue[Message]] = AtomicDict([(data_server,Queue()) for data_server in data_servers])

        self.base_data = base_data
        self.user_query_queue = user_query_queue
        self.query_result_queue = query_result_queue

        self.session_counter = AtomicCounter()

    def connect_all(self):
        for data_server in self.data_servers:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connections[data_server] = sock
            sock.setblocking(False)
            
            try:
                sock.connect(data_server.address)
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
                self.logger.put(f'[ERROR] Could not connect to data server at {data_server.address}.')
                raise Exception(f'Could not connect to data server at {data_server.address}.')
            
            self.logger.put(f'[NETWORK] Connected to data server at {data_server.address}.')

    def disconnect_all(self):
        for data_server in self.data_servers:
            conn = self.connections.get(data_server)
            if conn is not None:
                try:
                    conn.__exit__()
                    self.logger.put(f'[NETWORK] Disconnected from data server at {data_server.address}.')
                except Exception:
                    pass

    def make_request(self, recipient : DataServer, message : Message, responses : Optional[Queue] = None):
        self.logger.put(f'[NETWORK] Sending request to {recipient.address}: type `{message.type}`, id `{message.id}`, sid `{message.session_id}`.')
        conn = self.connections[recipient]
        conn.send(message.to_bytes())
        response = Message.from_bytes(buff=conn, stop_event=self.stop_event)
        self.logger.put(f'[NETWORK] Received response from {recipient.address}: type `{response.type}`, id `{response.id}`, sid `{response.session_id}`, data `{response.data}`.')
        
        if responses is None:
            return response
        responses.put((recipient,response))
        

    def request_all_data_servers(self, message: Message) -> list[tuple[DataServer, Message]]:
        responses = Queue()
        for data_server in self.data_servers:
            Thread(target=safe_thread_target(self.logger,self.stop_event,self.make_request),args=(data_server, message, responses)).start()
        
        result = []
        while not self.stop_event.is_set() and len(result) < len(self.data_servers):
            try:
                result.append(responses.get_nowait())
            except Empty:
                time.sleep(REFRESH_DELAY)
                pass
        if len(result) < len(self.data_servers):
            return None
        return result

    def run_key_exchange(self, session_id: int):
        self.logger.put(f'[KEY EXCHANGE] Key exchange started.')
        self.request_all_data_servers(Message(
            MessageType.KEY_EXCHANGE_INIT, data=self.data_server_ids, session_id=session_id))
        responses = self.request_all_data_servers(
            Message(MessageType.KEY_EXCHANGE_START, session_id=session_id))

        hashed_key = None
        for _, response in responses:
            response: Message
            if hashed_key is not None and hashed_key != response.data:
                self.logger.put(f'[ERROR] Key exchanged failed: different secret proofs "{hashed_key}" and "{response.data}".')
                self.stop_event.set()
                raise KeyExchangeError('Inconsistent proofs.')
            hashed_key = response.data
        self.logger.put(f'[KEY EXCHANGE] Key exchange done. proof: "{hashed_key}".')

    def query_ids(self, ids):
        session_id = self.session_counter.inc()
        self.run_key_exchange(session_id)
        merged_data = {}
        data_responses = self.request_all_data_servers(
            Message(MessageType.DATA_REQUEST, data=ids, session_id=session_id))
        for data_server, response in data_responses:
            data: list[tuple[str, Any]] = response.data
            self.logger.put(f'Data from {data_server.address}: {data}')
            for hashed_id, information in data:
                if hashed_id not in merged_data:
                    merged_data[hashed_id] = {}
                merged_data[hashed_id][data_server.id] = information
        return list(merged_data.values())

    def analysis_query(self, sample_conditions: Optional[ConditionsType] = None):
        study_group = filter_ids(self.base_data, sample_conditions)
        if len(study_group) < STUDY_GROUP_MINIMAL_SIZE:
            return []
        sample_ids = sample(study_group, min(ID_SAMPLE_SIZE, len(study_group)))
        res = self.query_ids(sample_ids)
        return res

    def run(self, stop_event: Event):
        try:
            self.stop_event = stop_event
            self.connect_all()
            self.logger.put('[NETWORK] Connected to all data_servers.')
            # result = self.analysis_query({'SysBP':Condition(BoundType.AT_LEAST,116)})
            # print('result:',result)
            while not stop_event.is_set():
                try:
                    message, conditional = self.user_query_queue.get_nowait()
                    conditional = conditional_from_struct(conditional)
                    result = self.analysis_query(conditional)
                    self.logger.put('results: ' + str(result))
                    self.query_result_queue.put((message, result))
                except Empty:
                    time.sleep(REFRESH_DELAY)
                    pass
        except Exception as e:
            self.logger.put(f'[ERROR-BACKEND] {e}')
            self.stop_event.set()
        finally:
            self.disconnect_all()
