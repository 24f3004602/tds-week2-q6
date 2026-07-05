import time
import uuid
from collections import deque
from datetime import datetime, timezone

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI()

# ── CORS: allow cross-origin requests ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup time for healthz ──
START_TIME = time.time()

# ── Prometheus counter (live, not static) ──
http_requests_total = Counter("http_requests_total", "Total HTTP requests")

# ── In-memory structured log store ──
MAX_LOGS = 1000
log_store = deque(maxlen=MAX_LOGS)

def push_log(level: str, path: str, request_id: str):
    log_store.append({
        "level": level,
        "ts": datetime.now(timezone.utc).isoformat(),
        "path": path,
        "request_id": request_id,
    })

# ── Middleware: count every request + log after completion ──
@app.middleware("http")
async def observe(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # Increment Prometheus counter for EVERY request
    http_requests_total.inc()

    response = await call_next(request)

    # Structured log entry
    push_log("info", request.url.path, request_id)
    return response

# ── Endpoints ──

@app.get("/work")
def work(n: int = Query(..., ge=0)):
    """Do K units of work and return."""
    # Actual CPU work so the endpoint isn't a no-op
    total = 0
    for i in range(n):
        total += i * i
    return {"email": "24f3004602@ds.study.iitm.ac.in", "done": n}

@app.get("/metrics")
def metrics():
    """Prometheus text format."""
    return PlainTextResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

@app.get("/healthz")
def healthz():
    """Health check with uptime."""
    uptime = time.time() - START_TIME
    return {"status": "ok", "uptime_s": round(uptime, 3)}

@app.get("/logs/tail")
def logs_tail(limit: int = Query(100, ge=1, le=1000)):
    """Return the last N structured log entries."""
    return list(log_store)[-limit:]
