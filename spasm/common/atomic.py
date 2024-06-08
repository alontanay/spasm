from typing import Any, TypeVar, Optional, Callable, Generic

import traceback
import time

from threading import Lock, Event
from queue import Queue

from spasm.common.error import UnresolvedPromise
from spasm.common.defaults import REFRESH_DELAY

_KT = TypeVar('_KT')
_VT = TypeVar('_VT')


class LockedDictContext(dict[_KT, _VT]):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class AtomicDict(Generic[_KT, _VT]):
    '''Locked Python dictionary, used as a context manager.'''

    def __init__(self, *args, **kwargs):
        self.__dict: LockedDictContext[_KT,
                                       _VT] = LockedDictContext(*args, **kwargs)
        self.__lock = Lock()

    def __enter__(self):
        self.__lock.acquire()
        return self.__dict

    def __exit__(self, *args):
        self.__lock.release()
        return False


class ImpliedEvent(Event):
    def __init__(self, super_event: Event, timeout: Optional[float] = None):
        self.super_event = super_event
        self.exclusive_event = Event()
        self.timeout_time = timeout and time.time()+timeout

    def set(self):
        self.exclusive_event.set()

    def is_set(self):
        return self.exclusive_event.is_set() or self.super_event.is_set() or self.timeout_time is not None and time.time() > self.timeout_time


class AtomicCounter:
    def __init__(self):
        self._val = 0
        self._lock = Lock()

    def get(self):
        with self._lock:
            return self._val

    def inc(self):
        with self._lock:
            self._val += 1
            return self._val

    def dec(self):
        with self._lock:
            self._val -= 1
            return self._val

    def set(self, val: int):
        with self._lock:
            self._val = val

    def block(self, stop_event: Optional[Event] = None):
        '''blocks until counter reaches zero (unreliable)'''
        while (stop_event is None or not stop_event.is_set()) and self.get():
            time.sleep(REFRESH_DELAY)


class Promise:
    '''
    Thread-safe value waiting assignment
    '''

    def __init__(self):
        self._lock = Lock()
        self._resolved = False

    def resolve(self, value):
        '''
        Only the creator of this instance should call this method. once.
        '''
        self._resolved = True
        self._value = value

    def resolved(self):
        '''
        Returns whether the promise is resolved.
        '''
        return self._resolved

    def get(self, blocking=False, timeout: float | None = None):
        '''
        Get value of promise. \n
        If unresolved, depending on the blocking parameter, either raises an `UnresolvedPromise` exception (blocking=`False`), or waits until resolved (blocking=`True`).
        '''
        if blocking:
            start_time = time.time()
            while not self._resolved and timeout is None or time.time()-start_time < timeout:
                time.sleep(REFRESH_DELAY)
                pass
        if not self._resolved:
            raise UnresolvedPromise
        return self._value


def safe_thread_target(logger: Queue, stop_event: Event, func: Callable):
    def new_func(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            logger.put(traceback.format_exc())
            logger.put(f'[ERROR] {e}')
            stop_event.set()
    return new_func
