from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import routes
from contextlib import asynccontextmanager
from redis import Redis, ConnectionError
from controllers.redis_controller import UploadController
import os

origins = [
    "http://localhost",
    "http://localhost:8080",
]

@asynccontextmanager
async def lifespan(router: FastAPI):
    try:
        redis_client = Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), db=0)
        if not redis_client.ping():
            raise ConnectionError("Redis connection failed")
        
        # Inicialize o Redis no router
        routes.router.state.redis = redis_client
        
        # Opcional: Inicialize o controller aqui se preferir
        routes.upload_controller = UploadController(redis_client)
        
        yield
        
    finally:
        if 'redis_client' in locals():
            redis_client.close()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount('/api', routes.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)