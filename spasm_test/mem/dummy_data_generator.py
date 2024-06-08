import json
import random
import string

from spasm_test import BASE_DATA, DATA_SERVERS

def rand_str(chars, length):
    return ''.join(chars[random.randint(0,len(chars)-1)] for _ in range(length))

ids = BASE_DATA.keys()

def boolean():
    def gen():
        return bool(random.randint(0,1))
    return gen

def floating(a, b):
    def gen():
        return round(a+random.random()*(b-a),2)
    return gen

def number(a, b):
    def gen():
        return random.randint(a,b)
    return gen

metas = [
    {'sysBP':number(90,150), 'diaBP': number(50, 100), 'planType': number(1,3)},
    {'hadSurgery':boolean(), 'totalCharge':floating(0,1000), 'numberOfVisits': number(1,10)},
    {'financialLoss':boolean(), 'riskFactor':floating(0,5)},
    {'married':boolean(), 'numberOfKids':number(0,6), 'salary': number(5800,30000)},
]

def generate_record(idx):
    desc = metas[idx]
    res ={}
    for key, gen in desc.items():
        res[key] = gen()
    return res

def generate_data(idx):
    data = {}
    for id in ids:
        data[id] = generate_record(idx)
    return data

for idx in range(len(DATA_SERVERS)):
    with open(f'mem/data_server{idx}.json','w') as f:
        print(generate_data(idx))
        json.dump(generate_data(idx),f)