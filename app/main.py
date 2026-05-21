import logfire
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routes import resume

# Configure Logfire (send to cloud only if token is present)
# Use the settings.LOGFIRE_TOKEN to decide whether to enable instrumentation.
logfire.configure(send_to_logfire='if-token')
if settings.LOGFIRE_TOKEN:
    logfire.instrument_pydantic()

app = FastAPI(
    title="Resume Parser API",
    description="API for parsing PDF resumes and extracting structured data",
    version="1.0.0",
)

# Instrument FastAPI only when a Logfire token is configured
if settings.LOGFIRE_TOKEN:
    logfire.instrument_fastapi(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


# Register routers
app.include_router(resume.router, prefix="/api/v1")
