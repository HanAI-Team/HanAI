from fastapi import FastAPI
from app.auth.router import router as auth_router
from app.diagnosis.router import router as diagnosis_router

# from app.charting.router import router as charting_router
from app.patients.router import router as patients_router

app = FastAPI(title="HanAI API")

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(diagnosis_router, prefix="/api/diagnosis", tags=["diagnosis"])
# app.include_router(charting_router, prefix="/api/charting", tags=["charting"])
app.include_router(patients_router, prefix="/api/patients", tags=["patients"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
