from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router_registry import include_api_routers


app = FastAPI(title="China Finance AI Assistant", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

include_api_routers(app)


@app.get("/health")
def health():
    return {"status": "ok"}
