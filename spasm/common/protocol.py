from typing import Optional, Union, Self, Any, overload
from dataclasses import dataclass
import socket

import json
from enum import Enum
from threading import Lock, Event
import time

from queue import Queue

from spasm.common.atomic import AtomicCounter, Promise
from spasm.common.error import ProtocolViolation, DataUnavailableError
from spasm.common.defaults import REFRESH_DELAY

class ByteBuffer:
    def __init__(self):
        self.buf = b''
        self.save_idx = 0
        self.idx = 0
        
    def recv(self, size):
        size = min(size,len(self.buf)-self.idx)
        self.idx += size
        return self.buf[self.idx-size:self.idx]
        
    def save(self):
        self.save_idx = self.idx
    
    def restore(self):
        self.idx = self.save_idx
    
    def append(self, data):
        if not data:
            raise DataUnavailableError
        self.buf += data

class BytesReader:
    def __init__(self, buf: bytes) -> None:
        self.buf = buf
        self.iter = iter(buf)

    def recv(self, size: int) -> bytes:
        try:
            return bytes([self.iter.__next__() for _ in range(size)])
        except StopIteration:
            raise DataUnavailableError()

def receive_exact_nonblock(socket: socket.socket, size: int, stop_event: Event) -> bytes:
    old_timeout = socket.gettimeout()
    
    try:
        socket.setblocking(False)
        res = b''
        while not stop_event.is_set() and len(res) < size:
            try:
                buf = socket.recv(size-len(res))
                res += buf
            except BlockingIOError:
                time.sleep(REFRESH_DELAY)
                pass
        if len(res) < size:
            raise DataUnavailableError()
        return res
    finally:
        socket.settimeout(old_timeout)


def receive_exact(readable: socket.socket | BytesReader | ByteBuffer, size: int, stop_event: Event | None = None) -> bytes:
    if stop_event is None:
        res = b''
        while len(res) < size and (buf := readable.recv(size-len(res))):
            res += buf
        if len(res) < size:
            raise DataUnavailableError()
        return res

    return receive_exact_nonblock(readable, size, stop_event)


MESSAGE_TYPE_NUMBER = 12


class MessageType(Enum):
    RESPONSE_OK, \
        RESPONSE_FAILED, \
\
        PING, \
        INFO, \
        RESET, \
\
        NEW_SESSION, \
        END_SESSION, \
\
        KEY_EXCHANGE_INIT, \
        KEY_EXCHANGE_START, \
        DATA_REQUEST, \
\
        KEY_EXCHANGE_STEP, \
\
        USER_DATA_REQUEST \
        = range(MESSAGE_TYPE_NUMBER)


_message_type_new = MessageType.__new__


def _new_message_type_new(self: MessageType, *args, **kwargs):
    if len(args) == 1 and (val := args[0]) >= MESSAGE_TYPE_NUMBER:
        raise ProtocolViolation(f'Invalid message type - {val}.')
    return _message_type_new(self, *args, **kwargs)


MessageType.__new__ = _new_message_type_new

id_counter = AtomicCounter()
id_counter.inc()

NO_DEFAULT = object()


@dataclass
class Message:
    TYPE_FIELDSIZE = 1
    ID_FIELDSIZE = 8
    SESSION_ID_FIELDSIZE = 8
    DATA_SIZE_FIELDSIZE = 3

    type: MessageType
    id: int
    session_id : int
    data: Any

    @overload
    def __init__(self, message: Self) -> None:
        '''Construct Message instance as a (shallow) copy of another'''
        pass

    @overload
    def __init__(self, type: int, data: Any = None, id: int = None, session_id : int = None) -> None:
        '''Construct Message instance from its properties.'''
        pass

    def __init__(self, type_or_obj: int | Self, data:int=None, id:int=None, session_id:int=None):
        if isinstance(type_or_obj, Message):
            self.type = type_or_obj.type
            self.data = type_or_obj.data
            self.id = type_or_obj.id
            self.session_id = type_or_obj.id
            return
        self.type = type_or_obj
        self.data = data
        self.id = id_counter.inc() % (1 << (Message.ID_FIELDSIZE*8)) if id is None else id
        self.session_id = 0 if session_id is None else session_id

    def generate_reply(self, success, data : Optional[Any]):
        response_type = MessageType.RESPONSE_OK if success else MessageType.RESPONSE_FAILED
        return Message(response_type, data, self.id, self.session_id)

    def from_bytes(bytes: bytes | None = None, buff: socket.socket | ByteBuffer | None = None, stop_event : Event = None) -> Self:
        '''
        [Static Method]
        Creates Message instance from bytes or a live socket connection to read from. \n
        A provided socket must be set to blocking. \n
        Raises ProtocolViolation in case data read doesn't match the protocol.
        '''
        res = Message(0)
        if bytes:
            reader = ByteBuffer(bytes)
        elif buff:
            reader = buff

        def get_next_bytes(size):
            return receive_exact(reader, size, stop_event)
        def get_next_int(size):
            return int.from_bytes(get_next_bytes(size),'little')

        type_num = get_next_int(Message.TYPE_FIELDSIZE)
        res.type = MessageType(type_num)
        res.id = get_next_int(Message.ID_FIELDSIZE)
        res.session_id = get_next_int(Message.SESSION_ID_FIELDSIZE)
        data_size = get_next_int(Message.DATA_SIZE_FIELDSIZE)
        res.decode_data(get_next_bytes(data_size))

        return res
    
    def check_data(self):
        # ! TODO
        pass

    def decode_data(self, payload):
        self.data = json.loads(payload) if payload != b'' else None
        self.check_data()

    def encode_data(self) -> bytes:
        return json.dumps(self.data).encode() if self.data is not None else b''

    def to_bytes(self) -> bytes:
        payload = self.encode_data()
        data_size = len(payload)
        try:
            res = self.type.value.to_bytes(Message.TYPE_FIELDSIZE, 'little') + \
                self.id.to_bytes(Message.ID_FIELDSIZE, 'little') + \
                self.session_id.to_bytes(Message.SESSION_ID_FIELDSIZE, 'little') + \
                data_size.to_bytes(Message.DATA_SIZE_FIELDSIZE, 'little')
        except OverflowError:
            raise ProtocolViolation('Header values exceeding limits.')
        res += payload
        return res

    def read_data(self, key: str | int | float | bool | None, default : Any=NO_DEFAULT):
        if self.data is None or key not in self.data:
            if default is not NO_DEFAULT:
                return default
            raise ProtocolViolation(
                f'Key \'{key}\' not found in data of message of type \'{self.type.name}\'.')
        return self.data[key]


def reply(conn: socket.socket, message: Message, data):
    conn.send(Message(MessageType.RESPONSE, data, message.id).to_bytes())

# class Ping(Message):
#     def __init__(self):
#         self.type = MessageType.PING


# class Info(Message):
#     def __init__(self):
#         self.type = MessageType.INFO

# class InitKeyExchange(Message):
#     def __init__(self, data_servers):
#         self.type = MessageType.INIT_KEY_EXCHANGE
#         self.data = data_servers

# class StartKeyExchange(Message):
#     def __init__(self):
#         self.type = MessageType.START_KEY_EXCHANGE