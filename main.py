import os
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from rooms import (
    create_room, list_rooms, get_room, join_room,
    save_snapshot, transfer_host
)

app = FastAPI(title="THE DARK TERMINAL", version="0.1.0")
STARTED_AT = time.time()

class CreateRoomRequest(BaseModel):
    player_id: str = Field(min_length=1, max_length=64)
    max_players: int = Field(default=4, ge=2, le=8)

class JoinRoomRequest(BaseModel):
    player_id: str = Field(min_length=1, max_length=64)

class SnapshotRequest(BaseModel):
    player_id: str
    version: int = Field(ge=1)
    snapshot: dict

class TransferHostRequest(BaseModel):
    old_host: str
    new_host: str
    expected_epoch: int = Field(ge=1)

@app.get("/")
def root():
    return {
        "service": "THE DARK TERMINAL",
        "status": "online",
        "version": "0.1.0"
    }

@app.get("/health")
def health():
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - STARTED_AT),
        "database_configured": bool(os.getenv("DATABASE_URL"))
    }

@app.get("/rooms")
def rooms():
    return {"rooms": list_rooms()}

@app.post("/rooms")
def new_room(body: CreateRoomRequest):
    return create_room(body.player_id, body.max_players)

@app.post("/rooms/{room_id}/join")
def join(room_id: str, body: JoinRoomRequest):
    room, error = join_room(room_id, body.player_id)
    if error:
        raise HTTPException(404 if error == "ROOM_NOT_FOUND" else 409, error)
    return room

@app.get("/rooms/{room_id}")
def room_details(room_id: str):
    room = get_room(room_id)
    if not room:
        raise HTTPException(404, "ROOM_NOT_FOUND")
    return room

@app.post("/rooms/{room_id}/snapshot")
def snapshot(room_id: str, body: SnapshotRequest):
    result, error = save_snapshot(
        room_id, body.player_id, body.version, body.snapshot
    )
    if error:
        raise HTTPException(404 if error == "ROOM_NOT_FOUND" else 409, error)
    return result

@app.post("/rooms/{room_id}/transfer-host")
def host_transfer(room_id: str, body: TransferHostRequest):
    result, error = transfer_host(
        room_id, body.old_host, body.new_host, body.expected_epoch
    )
    if error:
        raise HTTPException(404 if error == "ROOM_NOT_FOUND" else 409, error)
    return result
