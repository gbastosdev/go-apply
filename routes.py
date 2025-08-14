from typing import Dict
from fastapi import HTTPException, status, Cookie, UploadFile, File, Form, FastAPI
from fastapi.responses import JSONResponse
from controllers import redis_controller
import datetime

router = FastAPI()

@router.post("/resume_file/")
async def upload_file_endpoint(
    session_id: str = Cookie(None),
    cv: UploadFile = File(...)
):
    return await redis_controller.handle_upload(session_id, cv)

@router.post("/load_opportunity")
async def load_opportunity(session_id: str = Cookie(), opportunity: str = Form(...)) -> Dict[str, str]:
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID cookie is required",
        )
    
    # Verifica se a session existe
    if not router.state.redis.exists(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data found for this session",
        )
    
    # Obtém todos os metadados
    metadata = router.state.redis.hgetall(session_id)
    
    # Converte bytes para string (se estiver usando Redis py)
    metadata = {k.decode(): v.decode() for k, v in metadata.items()}
    
    return JSONResponse(
        status_code=200, 
        content=metadata
    )