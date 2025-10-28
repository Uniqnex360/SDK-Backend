import requests
import time
from openai import OpenAI
from openai import OpenAIError
from fastapi import HTTPException
import os
from dotenv import load_dotenv
load_dotenv()
OPEN_AI_KEY = os.getenv("OPEN_AI_KEY")
GOOGLE_GEMINI_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
client = OpenAI(api_key=OPEN_AI_KEY)


def ask_gemini(prompt: str, max_retries: int = 3) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GOOGLE_GEMINI_KEY}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        'contents': [{
            'parts': [{'text': prompt}]
        }]
    }
    last_error = None
    for attempt in range(max_retries):
        try:
            print(f"🔄 Gemini API attempt {attempt + 1}/{max_retries}")
            response = requests.post(
                url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                print(f"✅ Gemini API success on attempt {attempt + 1}")
                return result['candidates'][0]['content']['parts'][0]['text']
            last_error = "No response generated"
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            print(
                f"❌ Gemini API HTTP {status_code} error on attempt {attempt + 1}")
            if status_code in [503, 429, 500, 502, 504]:
                if attempt < max_retries - 1:
                    wait_time = 2 ** (attempt + 1)
                    print(f"⏳ Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                last_error = f"HTTP {status_code}"
            else:
                raise HTTPException(
                    status_code=status_code,
                    detail=f"Gemini API error: {e.response.text}"
                )
        except requests.exceptions.Timeout:
            print(f"⏰ Gemini API timeout on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            last_error = "Request timeout"
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            last_error = str(e)
    raise HTTPException(
        status_code=503,
        detail=f"AI service temporarily unavailable after {max_retries} attempts. Please try again in a moment."
    )


class ChatbotService:
    def __init__(self):
        self.openai_enabled = True
        self.gemini_enabled = True

    async def process_chat_message(
        self,
        user_query: str,
        product_context: dict,
        session_id: str = None
    ):
        try:
            product_name = product_context.get('name', 'this product')
            product_sku = product_context.get('sku', 'N/A')
            product_description = product_context.get('description', 'N/A')
            product_price = product_context.get('price', 'N/A')
            product_brand = product_context.get('brand', 'N/A')
            product_category = product_context.get('category', 'N/A')
            in_stock = product_context.get('inStock', True)
            product_info = f"""
Product Name: {product_name}
SKU: {product_sku}
Brand: {product_brand}
Category: {product_category}
Price: ${product_price}
Description: {product_description}
Availability: {'In Stock' if in_stock else 'Out of Stock'}
            """.strip()
            prompt = f"""
You are an AI assistant for an e-commerce website. Your task is to provide clear and relevant answers based on the given product details.
1. Answer concisely based only on the product details provided.
2. Avoid raw data dumps—only provide direct human-readable responses.
3. Keep responses under 200 words.
---
{product_info}
---
{user_query}
            """
            if self.openai_enabled:
                try:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system",
                                "content": "You are a helpful product assistant."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_tokens=300,
                        timeout=30
                    )
                    print("✅ Used OpenAI for response")
                    return response.choices[0].message.content.strip()
                except OpenAIError as e:
                    print(f"⚠️ OpenAI failed: {str(e)}")
            if self.gemini_enabled:
                try:
                    print("🔄 Falling back to Gemini...")
                    gemini_response = ask_gemini(prompt, max_retries=3)
                    print("✅ Used Gemini for response")
                    return gemini_response
                except HTTPException as e:
                    print(f"❌ Gemini also failed: {e.detail}")
                    raise HTTPException(
                        status_code=503,
                        detail="AI services are temporarily busy. Please try again in a few seconds."
                    )
            raise HTTPException(
                status_code=503,
                detail="AI services are currently unavailable."
            )
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Error in process_chat_message: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Error processing message: {str(e)}"
            )
