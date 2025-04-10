from fastapi import FastAPI, Form, HTTPException, File, UploadFile, Cookie,status
from fastapi.responses import JSONResponse
from typing import Annotated, Dict
import pickle, datetime

router = FastAPI()


@router.post("/resume_file/")
async def create_upload_file(session_id: str = Cookie(), opportunity: str = Form(...), cv: UploadFile = File(None)) -> Dict[str,str]:
    if session_id is None or not router.state.redis.get(session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID cookie is required",
        )
    try:
        contents = await cv.read()
        file_obj = {
            "cv": pickle.dumps(contents),  # The raw bytes of the PDF
            "opportunity": opportunity 
        }
        router.state.redis.set(session_id, file_obj, ex=datetime.timedelta(minutes=30)) 
        return JSONResponse(status_code=200, content="CV and Opportunity uploaded!")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
