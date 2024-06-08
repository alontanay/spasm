from typing import Callable, Iterable, overload, Any
from threading import Event, Lock
import time

from queue import Queue, Empty

from Crypto.Hash import SHA384

from spasm.common.atomic import AtomicCounter
from spasm.common.protocol import Message
from spasm.common.defaults import REFRESH_DELAY

from spasm.data_server.app import App

class Database:
    '''Implementation a database with Python's dictionary'''

    def __init__(self, data: dict):
        self._data = data

    def get(self, id):
        '''Returns a deep copy of the record of `id` in the database. Thread-safe.'''
        pass

    def write():
        '''Not Thread-safe'''
        pass


class DataComponent:
    def __init__(self, database: Database, logger : Queue):
        self.logger = logger
        self._reader_lock = Lock()
        self._database = database
        self._request_queue: Queue[tuple[Queue,
                                         Iterable[str], bytes]] = Queue()

    def write(self, callback: Callable[[Database], None]):
        with self._reader_lock:
            self.logger.put('[DATA] Writing...')
            callback(self._database)
            self.logger.put('[DATA] Done writing.')

    def _read(self, id_subset: Iterable[str], salt: bytes) -> list[tuple[str,Any]]:
        with self._reader_lock:
            self.logger.put(f'[DATA] Fetching... (secret salt: `{salt}`).')
            result = []
            base_hasher = SHA384.new(salt)
            for id in id_subset:
                hasher = base_hasher.copy()
                if data := self._database.get(id):
                    hasher.update(id.encode())
                    result.append((hasher.hexdigest(), data))
            result.sort()
            self.logger.put(f'[DATA] Done fetching.')
            return result

    def request(self, output_queue: Queue, request_id, id_subset: Iterable[str], salt: bytes):
        self._request_queue.put((output_queue, request_id, id_subset, salt))

    def run(self, stop_event: Event):
        self.logger.put('[DATA] Started database, waiting for requests.')
        while not stop_event.is_set():
            try:
                output_queue, request_id, id_subset, salt = self._request_queue.get_nowait()
                output_queue.put((request_id, self._read(id_subset, salt)))
            except Empty:
                time.sleep(REFRESH_DELAY)
                pass
        self.logger.put(f'[DATA] Closed database. approximately {self._request_queue.qsize()} requests lost.')
        