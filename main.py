from fastapi import FastAPI , Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import routes


app = FastAPI()


ALLOWED_ORIGINS = {"https://go-apply-frontend.vercel.app"}

@app.middleware("http")
async def restrict_origin_middleware(request: Request, call_next):
    origin = request.headers.get("origin")
    if origin not in ALLOWED_ORIGINS:
        raise HTTPException(status_code=403, detail="Forbidden")
    return await call_next(request)
app.mount('/api', routes.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)