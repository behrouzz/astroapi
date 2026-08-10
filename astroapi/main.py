from fastapi import FastAPI
from .routers import eop

app = FastAPI()

@app.get('/')
def test():
    return {'msg': 'API is working.'}

app.include_router(eop.router)