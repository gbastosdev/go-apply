from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.responses import JSONResponse
from typing import Annotated
import pickle

router = FastAPI()

@router.post("/get_file/")
async def get_file(file: Annotated[bytes, File()]):
    return {"file_size": len(file)}


@router.post("/resume_file/")
async def create_upload_file(file: UploadFile = File(...)):
    if not file:
        return {"message": "No upload file sent!"}	
    else:
        file_cached = router.state.redis.get(file.filename)
        if file_cached:
            return JSONResponse(status_code=200, content="File already uploaded!")
        else:
            try:
                contents = await file.read()
                file_obj = {
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "data": contents  # The raw bytes of the PDF
                }
                file = router.state.redis.set(file_obj["filename"], pickle.dumps(file_obj)) 
                return JSONResponse(status_code=200, content="File uploaded successfully!")
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
