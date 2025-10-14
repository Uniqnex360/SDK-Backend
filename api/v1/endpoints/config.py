from fastapi import APIRouter, Header, HTTPException
from models.schemas import ConfigResponse
from services.auth import verify_api_key
router=APIRouter()
@router.get('/config',response_model=ConfigResponse)
async def get_widget_config(x_api_key:str=Header(...,alias='X-API-KEY')):
    try:
        config=verify_api_key(x_api_key)
        return ConfigResponse(theme={
                "primary_color": "#1976d2",
                "secondary_color": "#fff",
                "background_color": "#f5f5f5",
                "font_family": "Arial, sans-serif"
            },
        position='bottom-right',
        greeting_message='Hello! Ask me about this product',
        placeholder='Type your message...')
    except Exception as e:
        raise HTTPException(status_code=500,detail=(str(e)))