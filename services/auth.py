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

def get_platform_config(api_key: str) -> dict:
    config = verify_api_key(api_key)
    if "shop_config" not in config:
        raise HTTPException(status_code=500, detail="Platform not configured for this API key")
    return config["shop_config"]

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
    
async def _call_internal_auth_check(customer_id: str, customer_token, x_api_key: str) -> dict:
    """Internal helper — calls our own /orders/auth-check (for orchestration layer)"""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "http://localhost:8000/api/v1/orders/auth-check",  # or use base_url from config
            headers={"X-API-Key": x_api_key, "Content-Type": "application/json"},
            json={"customer_id": customer_id, "customer_token": customer_token},
        )
        return resp.json()


async def _call_internal_verify(
    order_number: str,
    email: str,
    phone_last4: str,
    session_id: str,
    x_api_key: str,
) -> dict:
    """Internal helper — calls our own /orders/verify"""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "http://localhost:8000/api/v1/orders/verify",
            headers={
                "X-API-Key": x_api_key,
                "X-Session-Id": session_id,
                "Content-Type": "application/json",
            },
            json={
                "order_number": order_number,
                "email": email,
                "phone_last4": phone_last4,
            },
        )
        return resp.json()
