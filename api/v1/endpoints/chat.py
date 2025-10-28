from fastapi import APIRouter, Header, HTTPException
from models.schemas import ChatRequest, ChatResponse, ShopifyProduct, product_questions
from services.auth import verify_api_key, check_rate_limit
from services.chatbot_service import ChatbotService
from api.v1.endpoints.productdetails import get_product_details
router = APIRouter()
chatbot_service = ChatbotService()


@router.post('/chat', response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, x_api_key: str = Header(..., alias="X-API-Key")):
    try:
        config = verify_api_key(x_api_key)
        check_rate_limit(x_api_key, config['rate_limit'])
        user_query = request.message.strip()
        product_context = request.product_context
        
        if not user_query:
            raise HTTPException(status_code=400, detail="Message is required")
        
        needs_full_details = False
        shopify_product_id = None
        
        if product_context:
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
        
        if needs_full_details:
            print(f"🔍 Fetching full details for Shopify product ID: {shopify_product_id}")
            try:
                product_response = await get_product_details(shopify_product_id, x_api_key)
                product_context = product_response
                print(f" Fetched product details: {product_context.get('title', 'N/A')}")
            except Exception as e:
                print(f" Failed to fetch product details: {str(e)}")
                raise HTTPException(
                    status_code=404, 
                    detail=f"Could not fetch product details for ID {shopify_product_id}: {str(e)}"
                )
        
        if not product_context or not (product_context.get('title') or product_context.get('name')):
            raise HTTPException(status_code=400, detail="Valid product context is required")
        
        # Check if answer exists in database first
        product_obj = None
        category_obj = None
        
        if shopify_product_id:
            try:
                # Get the product's category
                product_obj = ShopifyProduct.objects.get(_id=shopify_product_id)
                category_obj = product_obj.category_id
                
                if category_obj:
                    print(f"🔍 Checking database for existing answer...")
                    
                    # 👇 SIMPLIFIED: Only exact match (case-insensitive)
                    matching_question = product_questions.objects(
                        category_id=category_obj,
                        question__iexact=user_query  # 👈 Exact match only
                    ).first()
                    
                    if matching_question:
                        print(f" Found exact match in database!")
                        print(f"   Question: {matching_question.question}")
                        print(f"   Answer: {matching_question.answer[:100]}...")
                        
                        return ChatResponse(
                            response=matching_question.answer,
                            session_id=request.session_id,
                            product_id=product_context.get('sku', product_context.get('productId', 'unknown'))
                        )
                    else:
                        print(f"ℹ️ No exact match found in database, proceeding with AI")
                else:
                    print(f"ℹ️ Product has no category assigned, proceeding with AI")
                    
            except ShopifyProduct.DoesNotExist:
                print(f"ℹ️ Product not found in database, proceeding with AI")
            except Exception as e:
                print(f"⚠️ Error checking database: {str(e)}, proceeding with AI")
        
        # If no match found in database, use AI chatbot
        print(f"🤖 Using AI to generate response...")
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
# async def chat_endpoint(request: ChatRequest, x_api_key: str = Header(..., alias="X-API-Key")):
#     try:
#         config = verify_api_key(x_api_key)
#         check_rate_limit(x_api_key, config['rate_limit'])
#         user_query = request.message.strip()
#         product_context = request.product_context
#         if not user_query:
#             raise HTTPException(status_code=400, detail="Message is required")
#         needs_full_details = False
#         if product_context:
#             if (product_context.get('sku') == 'shopify' or
#                 product_context.get('title') == 'Loading...' or
#                 'productId' in product_context):
#                 needs_full_details = True
#                 shopify_product_id = product_context.get('productId')
#         elif request.product_id:
#             needs_full_details = True
#             shopify_product_id = request.product_id
#         else:
#             raise HTTPException(status_code=400, detail="Product context or product_id is required")
#         if needs_full_details:
#             print(f"🔍 Fetching full details for Shopify product ID: {shopify_product_id}")
#             try:
#                 product_response = await get_product_details(shopify_product_id, x_api_key)
#                 product_context = product_response
#                 print(f" Fetched product details: {product_context.get('title', 'N/A')}")
#             except Exception as e:
#                 print(f"Failed to fetch product details: {str(e)}")
#                 raise HTTPException(
#                     status_code=404,
#                     detail=f"Could not fetch product details for ID {shopify_product_id}: {str(e)}"
#                 )
#         if not product_context or not (product_context.get('title') or product_context.get('name')):
#             raise HTTPException(status_code=400, detail="Valid product context is required")
#         response_text = await chatbot_service.process_chat_message(
#             user_query,
#             product_context,
#             request.session_id
#         )
#         return ChatResponse(
#             response=response_text,
#             session_id=request.session_id,
#             product_id=product_context.get('sku', product_context.get('productId', 'unknown'))
#         )
#     except HTTPException:
#         raise
#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
