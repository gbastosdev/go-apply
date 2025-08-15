from typing import Dict
from fastapi import HTTPException, status, Cookie, UploadFile, File, Form, FastAPI
from fastapi.responses import JSONResponse
from controllers import rag_controller

router = FastAPI()

@router.post("/resume_file/")
async def upload_file_endpoint(cv: UploadFile = File(...), opportunity: str = Form(...)):
    """Process the opportunity and CV upload"""
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Opportunity is required",
        )

    if cv.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed",
        )

    try:
        contents = await cv.read()
        
        return {"message": await rag_controller.analyze_job_cv(opportunity, contents).get("response", "An error occurred while processing the CV.")}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar arquivo: {str(e)}"
        )
    # return await redis_controller.handle_upload(session_id, cv)

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