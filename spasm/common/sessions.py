from typing import Callable, TypeVar

from enum import Enum

from threading import Thread, Event, Lock

from queue import Queue

from spasm.common.protocol import Message
from spasm.common.network_components import NetworkComponent


class SessionState(Enum):
    pass

class SessionContext[SessionStateType : SessionState]:
    id: int
    kill_event: Event
    logger: Queue
    state: SessionStateType

    def __init__(self, id : int, kill_event : Event, logger : Queue, state : SessionStateType):
        self.id = id
        self.kill_event = kill_event
        self.logger = logger
        self.state = state


class SessionWrapper[SessionContextType : SessionContext]:
    def __init__(self, session: SessionContextType):
        self._session = session
        self._lock = Lock()

    def __enter__(self):
        self._lock.acquire()
        return self._session

    def __exit__(self):
        self._lock.release()


class CommunicationSession[SessionWrapperType : SessionWrapper]:
    session_id: int
    session_wrapper: SessionWrapperType

    kill_event: Event
    thread: Thread

    incoming_requests: Queue[tuple[NetworkComponent, Message]]

    def __init__(self, session_id: int, handler: Callable, session_wrapper : SessionWrapperType):
        self.session_id = session_id
        self.session_wrapper = session_wrapper
        self.kill_event = Event()
        self.incoming_requests = Queue()

        self.thread = Thread(target=handler, args=(
            self, self.kill_event))
        self.thread.start()

    def kill(self):
        self.kill_event.set()