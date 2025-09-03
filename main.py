from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import routes

origins = [
    "http://localhost",
    "https://go-apply-production.up.railway.app"
]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount('/api', routes.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)