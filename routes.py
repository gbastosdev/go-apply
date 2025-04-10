import json
from fastapi import FastAPI, Form, HTTPException, File, UploadFile, Cookie, status
from fastapi.responses import JSONResponse
from typing import Annotated, Dict
import pickle, datetime

router = FastAPI()


@router.post("/resume_file/")
async def create_upload_file(session_id: str = Cookie(), opportunity: str = Form(...), cv: UploadFile = File(...)) -> Dict[str,str]:
    if session_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID cookie is required",
        )
    router.state.redis.get(session_id)
    try:
        contents = await cv.read()
        file_obj = {
            "cv": contents,  # The raw bytes of the PDF
            "opportunity": opportunity 
        }
        router.state.redis.set(session_id, pickle.dumps(file_obj), ex=datetime.timedelta(minutes=30)) 
        return JSONResponse(status_code=200, content="CV and Opportunity uploaded!")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
