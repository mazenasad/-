import secrets
import time
from threading import RLock

_lock = RLock()
_rooms = {}

def create_room(owner_id: str, max_players: int = 4):
    room_id = secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:8].upper()

    room = {
        "room_id": room_id,
        "owner_id": owner_id,
        "host_id": owner_id,
        "host_epoch": 1,
        "max_players": max(2, min(max_players, 8)),
        "players": [owner_id],
        "status": "waiting",
        "created_at": time.time(),
        "snapshot": None,
        "snapshot_version": 0,
    }

    with _lock:
        _rooms[room_id] = room

    return dict(room)

def list_rooms():
    with _lock:
        return [
            {
                "room_id": r["room_id"],
                "players": len(r["players"]),
                "max_players": r["max_players"],
                "status": r["status"],
            }
            for r in _rooms.values()
        ]

def get_room(room_id: str):
    with _lock:
        room = _rooms.get(room_id.upper())
        return dict(room) if room else None

def join_room(room_id: str, player_id: str):
    with _lock:
        room = _rooms.get(room_id.upper())
        if not room:
            return None, "ROOM_NOT_FOUND"

        if player_id not in room["players"]:
            if len(room["players"]) >= room["max_players"]:
                return None, "ROOM_FULL"
            room["players"].append(player_id)

        return dict(room), None

def save_snapshot(room_id: str, player_id: str, version: int, snapshot: dict):
    with _lock:
        room = _rooms.get(room_id.upper())
        if not room:
            return None, "ROOM_NOT_FOUND"

        if player_id != room["host_id"]:
            return None, "HOST_ONLY"

        if version <= room["snapshot_version"]:
            return None, "STALE_VERSION"

        room["snapshot"] = snapshot
        room["snapshot_version"] = version
        return {"version": version}, None

def transfer_host(room_id: str, old_host: str, new_host: str, expected_epoch: int):
    with _lock:
        room = _rooms.get(room_id.upper())
        if not room:
            return None, "ROOM_NOT_FOUND"

        if room["host_id"] != old_host:
            return None, "NOT_CURRENT_HOST"

        if room["host_epoch"] != expected_epoch:
            return None, "STALE_HOST_EPOCH"

        if new_host not in room["players"]:
            return None, "NEW_HOST_NOT_IN_ROOM"

        room["host_id"] = new_host
        room["host_epoch"] += 1

        return {
            "host_id": new_host,
            "host_epoch": room["host_epoch"],
            "snapshot_version": room["snapshot_version"],
        }, None
              
