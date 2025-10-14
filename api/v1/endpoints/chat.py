from fastapi import APIRouter, Header, HTTPException
from models.schemas import ChatRequest, ChatResponse
from services.auth import verify_api_key, check_rate_limit
from services.chatbot_service import ChatbotService

router = APIRouter()
chatbot_service = ChatbotService()
@router.post('/chat',response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest,x_api_key: str = Header(..., alias="X-API-Key")):
    try:
        print("HEE",x_api_key)
        config=verify_api_key(x_api_key)
        check_rate_limit(x_api_key,config['rate_limit'])
        user_query=request.message.strip()
        product_id=request.product_id
        if not user_query or not product_id:
            raise HTTPException(status_code=400,detail="Message and product_id are required")
        response_text=await chatbot_service.process_chat_message(user_query,product_id,request.session_id)
        return ChatResponse(response=response_text,session_id=request.session_id,product_id=product_id)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500,detail=f"Server error{str(e)}")
        
