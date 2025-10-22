from fastapi import APIRouter, Header, HTTPException
from models.schemas import ChatRequest, ChatResponse
from services.auth import verify_api_key, check_rate_limit
from services.chatbot_service import ChatbotService
from api.v1.endpoints.productdetails import get_product_details
router = APIRouter()
chatbot_service = ChatbotService()
@router.post('/chat',response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, x_api_key: str = Header(..., alias="X-API-Key")):
    try:
        config = verify_api_key(x_api_key)
        check_rate_limit(x_api_key, config['rate_limit'])
        
        user_query = request.message.strip()
        product_context = request.product_context
        
        if not user_query:
            raise HTTPException(status_code=400, detail="Message is required")
        
        # ✅ Check if we need to fetch full product details
        needs_full_details = False
        
        if product_context:
            # Check if it's a placeholder context (only has productId and minimal data)
            if (product_context.get('sku') == 'shopify' or 
                product_context.get('title') == 'Loading...' or
                'productId' in product_context):
                needs_full_details = True
                shopify_product_id = product_context.get('productId')
        elif request.product_id:
            needs_full_details = True
            shopify_product_id = request.product_id
        else:
            raise HTTPException(status_code=400, detail="Product context or product_id is required")
        
        # ✅ Fetch full product details if needed
        if needs_full_details:
            print(f"🔍 Fetching full details for Shopify product ID: {shopify_product_id}")
            try:
                product_response = await get_product_details(
                    type('Request', (), {'product_id': str(shopify_product_id)})(),
                    x_api_key
                )
                product_context = product_response
                print(f"✅ Fetched product details: {product_context.get('title', 'N/A')}")
            except Exception as e:
                print(f"❌ Failed to fetch product details: {str(e)}")
                raise HTTPException(
                    status_code=404, 
                    detail=f"Could not fetch product details for ID {shopify_product_id}: {str(e)}"
                )
        
        if not product_context or not product_context.get('title'):
            raise HTTPException(status_code=400, detail="Valid product context is required")
        
        # Process chat message with full product context
        response_text = await chatbot_service.process_chat_message(
            user_query,
            product_context,
            request.session_id
        )
        
        return ChatResponse(
            response=response_text,
            session_id=request.session_id,
            product_id=product_context.get('sku', product_context.get('productId', 'unknown'))
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")