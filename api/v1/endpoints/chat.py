from fastapi import APIRouter, Header, HTTPException
from models.schemas import ChatRequest, ChatResponse
from services.auth import verify_api_key, check_rate_limit
from services.chatbot_service import ChatbotService

router = APIRouter()
chatbot_service = ChatbotService()
@router.post('/chat',response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, x_api_key: str = Header(..., alias="X-API-Key")):
    try:
        print("Received request:", request.dict())
        print("API Key:", x_api_key)
        
        config = verify_api_key(x_api_key)
        check_rate_limit(x_api_key, config['rate_limit'])
        
        user_query = request.message.strip()
        product_context = request.product_context  # ✅ Get product context
        
        if not user_query:
            raise HTTPException(status_code=400, detail="Message is required")
        
        if not product_context:
            raise HTTPException(status_code=400, detail="Product context is required")
        
        # ✅ Pass product_context and session_id correctly
        response_text = await chatbot_service.process_chat_message(
            user_query,
            product_context,  # ✅ Pass product context, not product_id
            request.session_id
        )
        
        return ChatResponse(
            response=response_text,
            session_id=request.session_id,
            product_id=product_context.get('sku', 'unknown')  # ✅ Add product_id from SKU
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print("Error:", e)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")