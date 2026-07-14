
import os
import time
import jwt
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import HTTPException
from typing import Optional

from services.auth import verify_api_key  

JWT_SECRET = os.getenv("ORDER_VERIFY_JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("ORDER_VERIFY_JWT_SECRET not set — required for order verify tokens")

VERIFY_TOKEN_TTL_MIN = 10  



order_verify_attempts = defaultdict(list)

def check_order_verify_rate_limit(api_key: str, session_id: str, limit: int = 5, window_sec: int = 900):
   
    key = f"{api_key}:{session_id}"
    now = time.time()
    window_start = now - window_sec
    order_verify_attempts[key] = [t for t in order_verify_attempts[key] if t > window_start]
    if len(order_verify_attempts[key]) >= limit:
        raise HTTPException(status_code=429, detail="Too many order lookup attempts. Please try again later or contact support.")
    order_verify_attempts[key].append(now)




async def verify_customer_token(customer_token: Optional[str], customer_id: Optional[str], platform_adapter) -> Optional[str]:
    
    if not customer_token and not customer_id:
        return None
    try:
        verified_id = await platform_adapter.verify_customer(customer_token, customer_id)
        return verified_id  
    except Exception as e:
        print(f"⚠️ customer token verify failed: {e}")
        return None  




async def verify_guest_order(order_number: str, email: Optional[str], phone_last4: Optional[str], platform_adapter) -> Optional[str]:
        
    if not email and not phone_last4:
        raise HTTPException(status_code=400, detail="Provide email or phone (last 4 digits) to verify order ownership")

    try:
        order_id = await platform_adapter.match_order(order_number, email, phone_last4)
        return order_id
    except Exception as e:
        print(f"⚠️ guest order verify failed: {e}")
        return None




def issue_verify_token(order_id: str, customer_id: Optional[str] = None) -> str:
    payload = {
        "order_id": order_id,
        "customer_id": customer_id,
        "exp": datetime.utcnow() + timedelta(minutes=VERIFY_TOKEN_TTL_MIN),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def validate_verify_token(token: str) -> dict:
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Order verification expired, please verify again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid verification token")