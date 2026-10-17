from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import edition, refresh, pdf_export
from mangum import Mangum

app = FastAPI(title="Edition of One API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(edition.router, prefix="/api/edition", tags=["edition"])
app.include_router(refresh.router, prefix="/dev", tags=["dev"])
app.include_router(pdf_export.router, prefix="/api/edition", tags=["pdf"])

@app.get("/")
def read_root():
    return {"status": "online", "message": "Edition of One API is running on Vercel"}

# Serverless handler for Vercel
handler = Mangum(app)