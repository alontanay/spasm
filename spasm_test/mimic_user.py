import socket
from spasm_test import MAIN_SERVER

from spasm.common.protocol import Message, MessageType
from spasm.common.queries import Condition, ConditionsType, BoundType, filter_ids


def make_query(sock : socket.socket, *args):
    sz = len(args)
    if sz&1:
        raise Exception('*args correct form: (property_name, condition, ...), therefore must be even in length.')
    conditions = {}
    for i in range(0,sz,2):
        property_name = args[i]
        condition : Condition = args[i+1]
        conditions[property_name] = condition.to_struct()
    
    print(args,conditions)
    sock.send(Message(MessageType.USER_DATA_REQUEST,conditions).to_bytes())
    print('RESULT')
    response =  Message.from_bytes(buff=sock)
    for idx, info in enumerate(response.data):
        print(f'{idx}.\t', info)
    

with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
    sock.connect(MAIN_SERVER.LOOPBACK_ADDRESS)
    sock.send(Message(MessageType.PING).to_bytes())
    print(Message.from_bytes(buff=sock))
    
    make_query(sock)
    make_query(sock, 'age', Condition(BoundType.AT_LEAST,50))
    make_query(sock, 'sex', Condition(BoundType.NOT,'M'))
    make_query(sock, 'age', Condition(BoundType.AT_LEAST,50))