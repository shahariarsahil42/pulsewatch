from datetime import datetime, timezone

from fastapi import FastAPI


app = FastAPI(
    title="PulseWatch API",
    description="Real-time application monitoring platform",
    version="0.1.0",
)


@app.get("/")
def read_root():
    return {
        "message": "PulseWatch API is running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }