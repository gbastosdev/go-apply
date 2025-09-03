from fastapi import FastAPI , Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import routes

app = FastAPI()

ALLOWED_IPS = {"187.36.173.62"}  # conjunto de IPs permitidos

@app.middleware("http")
async def restrict_ip_middleware(request: Request, call_next):
    client_host = request.client.host
    if client_host not in ALLOWED_IPS:
        raise HTTPException(status_code=403, detail="Forbidden")
    return await call_next(request)
app.mount('/api', routes.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)