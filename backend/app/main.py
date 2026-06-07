from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.api.upload import router as upload_router

load_dotenv()

app = FastAPI(
    title="Dataplant API",
    description="Pipeline Excel → IA → datos normalizados para el sector metal",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, prefix="/api")


@app.get("/")
async def root():
    return {"mensaje": "Dataplant API funcionando", "docs": "/docs"}
