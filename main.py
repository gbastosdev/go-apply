from fastapi import FastAPI , Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import routes


app = FastAPI()


ALLOWED_IPS = {"https://go-apply-frontend.vercel.app/"}

@app.middleware("http")
async def restrict_ip_middleware(request: Request, call_next):
    # Tenta pegar IP real do cliente
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        client_ip = x_forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host

    if client_ip not in ALLOWED_IPS:
        raise HTTPException(status_code=403, detail="Forbidden")

    return await call_next(request)

app.mount('/api', routes.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)