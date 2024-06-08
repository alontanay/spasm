class ProtocolViolation(Exception):
    def __init__(self, message):
        super().__init__(f'ProtocolViolation: {message}')
        self.message = message

class UnresolvedPromise(Exception):
    def __init__(self, message):
        super().__init__(f'UnresolvedPromise: {message}')
        self.message = message

class DataUnavailableError(Exception):
    pass
