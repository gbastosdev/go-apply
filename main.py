from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import routes
from contextlib import asynccontextmanager
from redis import Redis
import httpx
import os

origins = [
    "http://localhost",
    "http://localhost:8080",
]

@asynccontextmanager
async def lifespan(router: FastAPI):
    try:
        routes.router.state.redis = Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), db=0)
        routes.router.state.client = httpx.AsyncClient()
        yield
        router.state.redis.close()
    except Exception as e:
        print(e)

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