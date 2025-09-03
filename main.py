from fastapi import FastAPI , Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import routes


app = FastAPI()

app.mount('/api', routes.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)