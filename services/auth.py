import time
from collections import defaultdict
from fastapi import HTTPException
API_KEYS={
    'demo_key_12345':{
        'name':"Demo store",
        "domain":"*",
        "rate_limit":100
    }
}
rate_limit_store = defaultdict(list)
def verify_api_key(api_key:str)->dict:
    if api_key not in API_KEYS:
        raise HTTPException(status_code=401,detail='Invalid API KEY')
    return API_KEYS[api_key]

def check_rate_limit(api_key:str,limit:int=100):
    now=time.time()
    hour_ago=now-3600
    rate_limit_store[api_key]=[
        req_time for req_time in rate_limit_store[api_key]
        if req_time>hour_ago
    ]
    if len(rate_limit_store[api_key])>=limit:
        raise HTTPException(status_code=429,detail='Rate limit exceeded')
    rate_limit_store[api_key].append(now)
