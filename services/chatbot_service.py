from openai import OpenAI
from openai import OpenAIError
from fastapi import HTTPException
import os
from dotenv import load_dotenv

load_dotenv()

OPEN_AI_KEY = os.getenv("OPEN_AI_KEY")
GOOGLE_GEMINI_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")

client = OpenAI(api_key=OPEN_AI_KEY)


def ask_gemini(prompt):
    import requests
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GOOGLE_GEMINI_KEY}"

    headers = {'Content-Type': 'application/json'}
    payload = {
        'contents': [{
            'parts': [{'text': prompt}]
        }]
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        if 'candidates' in result and len(result['candidates']) > 0:
            return result['candidates'][0]['content']['parts'][0]['text']
        return "Sorry, I couldn't generate a response."
    except Exception as e:
        return f"Error: {str(e)}"


class ChatbotService:
    def __init__(self):
        pass

    async def process_chat_message(
        self,
        user_query: str,
        product_context: dict,  # ✅ Changed from product_id
        session_id: str = None
    ):
        """
        Process chat message using product context from frontend
        No database lookup needed - all data comes from frontend
        """
        # print(f'PRODUCTCONTENTETETETETE: {product_context}')

        try:
            # ✅ Extract product info from context
            product_name = product_context.get('name', 'this product')
            product_sku = product_context.get('sku', 'N/A')
            product_description = product_context.get('description', 'N/A')
            product_price = product_context.get('price', 'N/A')
            product_brand = product_context.get('brand', 'N/A')
            product_category = product_context.get('category', 'N/A')
            in_stock = product_context.get('inStock', True)
            print('productksu',product_context.get('variants', [{}])[0].get('id'))
            # Build product info string
            product_info = f"""
Product Name: {product_name}
SKU: {product_sku}
Brand: {product_brand}
Category: {product_category}
Price: ${product_price}
Description: {product_description}
Availability: {'In Stock' if in_stock else 'Out of Stock'}
            """.strip()

            # Create prompt
            prompt = f"""
You are an AI assistant for an e-commerce website. Your task is to provide clear and relevant answers based on the given product details.

### Instructions:
1. Answer concisely based only on the product details provided.
3. Avoid raw data dumps—only provide direct human-readable responses.

---

### Product Information:
{product_info}

---

### User Query:
{user_query}

### AI Response:
            """

            # Try OpenAI first, fallback to Gemini
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system",
                            "content": "You are a helpful product assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=300
                )
                return response.choices[0].message.content.strip()
            except OpenAIError as e:
                print(f"OpenAI failed, falling back to Gemini: {str(e)}")
                return ask_gemini(prompt)

        except Exception as e:
            print(f"Error in process_chat_message: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500, detail=f"Error processing message: {str(e)}")
