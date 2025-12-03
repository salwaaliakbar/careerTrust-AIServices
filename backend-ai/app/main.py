from fastapi import FastAPI
from app.face_routes import router as face_router
from app.resume_routes import router as resume_router

app = FastAPI(title="CareerTrust AI Services")

# Mount service routers at root so original paths remain unchanged
app.include_router(face_router)
app.include_router(resume_router)


# root health
@app.get("/")
def root():
    return {"ok": True, "services": ["face-recognition", "parse-resume"]}
