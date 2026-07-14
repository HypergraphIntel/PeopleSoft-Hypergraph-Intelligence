import secrets
import string
from pathlib import Path
import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from passlib.hash import argon2
from datetime import datetime, timezone
import json

from routers import authelia_admin
from connectors import psdb
from connectors import paths

router = APIRouter(prefix="/api/identity", tags=["Identity"])

ROLE_MAP_FILE    = paths.APP_ROOT / "config/role_mapping.yml"
AUDIT_FILE       = paths.LOG_DIR / "identity_audit.jsonl"
REQUESTS_FILE    = paths.LOG_DIR / "provision_requests.json"

class ProvisionRequest(BaseModel):
    password: str


class BulkProvisionRequest(BaseModel):
    oprids: list[str]
    password: str | None = None  # if None, auto-generate per user


class ProvisionRequestCreate(BaseModel):
    oprid: str
    reason: str = ""
    requested_by: str = "admin"


class ProvisionRequestReject(BaseModel):
    reason: str = ""


def load_role_map():
    if not ROLE_MAP_FILE.exists():
        return {}
    return yaml.safe_load(ROLE_MAP_FILE.read_text()) or {}


def audit(action: str, target: str, detail: dict):
    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "target": target,
        "detail": detail,
    }

    with AUDIT_FILE.open("a") as f:
        f.write(json.dumps(event) + "\n")


@router.get("/compare/{oprid}")
def compare_identity(oprid: str, env: str = psdb.default_env()):
    oprid = oprid.upper()

    ps_user = psdb.oprid(oprid, env)
    roles = psdb.oprid_roles(oprid, env)

    role_map = load_role_map()
    mapped_groups = set()

    for r in roles:
        for g in role_map.get(r["rolename"], []):
            mapped_groups.add(g)

    authelia = authelia_admin.load_db()
    authelia_user = authelia["users"].get(oprid)

    return {
        "oprid": oprid,
        "peoplesoft": ps_user,
        "roles": roles,
        "mapped_groups": sorted(mapped_groups),
        "authelia_exists": authelia_user is not None,
        "authelia": {
            "email": authelia_user.get("email"),
            "groups": authelia_user.get("groups", []),
            "disabled": authelia_user.get("disabled", False),
        } if authelia_user else None
    }


@router.post("/sync/{oprid}")
def sync_identity(oprid: str, env: str = psdb.default_env()):
    comparison = compare_identity(oprid, env)
    oprid = comparison["oprid"]

    if not comparison["peoplesoft"]:
        return {"status": "error", "message": "PeopleSoft OPRID not found"}

    if not comparison["authelia_exists"]:
        return {"status": "error", "message": "Authelia user does not exist"}

    data = authelia_admin.load_db()
    user = data["users"][oprid]

    old_groups = set(user.get("groups", []))
    new_groups = set(comparison["mapped_groups"])

    old_disabled = user.get("disabled", False)
    new_disabled = comparison["peoplesoft"].get("acctlock") != 0

    old_displayname = user.get("displayname")
    new_displayname = comparison["peoplesoft"].get("oprdefndesc") or oprid

    user["displayname"] = new_displayname
    user["groups"] = sorted(new_groups)
    user["disabled"] = new_disabled

    authelia_admin.save_db(data)


    result = {
        "status": "synced",
        "oprid": oprid,
        "groups": {
            "added": sorted(new_groups - old_groups),
            "removed": sorted(old_groups - new_groups),
            "unchanged": sorted(old_groups & new_groups),
            "current": sorted(new_groups),
        },
        "disabled": {
            "old": old_disabled,
            "new": new_disabled,
            "changed": old_disabled != new_disabled,
        },
        "displayname": {
            "old": old_displayname,
            "new": new_displayname,
            "changed": old_displayname != new_displayname,
        }
    }

    audit("sync_identity", oprid, result)
    return result


@router.post("/provision/{oprid}")
def provision_identity(oprid: str, req: ProvisionRequest, env: str = psdb.default_env()):
    comparison = compare_identity(oprid, env)
    oprid = comparison["oprid"]

    if not comparison["peoplesoft"]:
        return {"status": "error", "message": "PeopleSoft OPRID not found"}

    if comparison["authelia_exists"]:
        return {"status": "error", "message": "Authelia user already exists"}

    data = authelia_admin.load_db()

    data["users"][oprid] = {
        "disabled": comparison["peoplesoft"].get("acctlock") != 0,
        "displayname": comparison["peoplesoft"].get("oprdefndesc") or oprid,
        "password": argon2.hash(req.password),
        "email": f"{oprid.lower()}@deathstar.chickenkiller.com",
        "groups": comparison["mapped_groups"],
    }

    authelia_admin.save_db(data)

    result = {
        "status": "provisioned",
        "oprid": oprid,
        "groups": comparison["mapped_groups"],
        "disabled": data["users"][oprid]["disabled"],
    }

    audit("provision_identity", oprid, result)
    return result

def _gen_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.post("/bulk-provision")
def bulk_provision(req: BulkProvisionRequest, env: str = psdb.default_env()):
    """Provision multiple PeopleSoft operators into Authelia in one call.

    Returns a result per OPRID: provisioned, skipped (already exists), or error.
    If req.password is None, generates a unique random password per user.
    """
    data = authelia_admin.load_db()
    results = []

    for oprid in req.oprids:
        oprid = oprid.strip().upper()
        if not oprid:
            continue
        try:
            comparison = compare_identity(oprid, env)
            if not comparison["peoplesoft"]:
                results.append({"oprid": oprid, "status": "not_found_in_peoplesoft"})
                continue
            if comparison["authelia_exists"]:
                results.append({"oprid": oprid, "status": "already_exists"})
                continue
            password = req.password or _gen_password()
            data["users"][oprid] = {
                "disabled": comparison["peoplesoft"].get("acctlock") != 0,
                "displayname": comparison["peoplesoft"].get("oprdefndesc") or oprid,
                "password": argon2.hash(password),
                "email": f"{oprid.lower()}@deathstar.chickenkiller.com",
                "groups": comparison["mapped_groups"],
            }
            results.append({
                "oprid": oprid,
                "status": "provisioned",
                "groups": comparison["mapped_groups"],
                "temp_password": password if not req.password else "(shared)",
            })
        except Exception as exc:
            results.append({"oprid": oprid, "status": "error", "error": str(exc)})

    if any(r["status"] == "provisioned" for r in results):
        authelia_admin.save_db(data)

    provisioned_count = sum(1 for r in results if r["status"] == "provisioned")
    result = {
        "status": "complete",
        "provisioned": provisioned_count,
        "skipped": sum(1 for r in results if r["status"] == "already_exists"),
        "errors": sum(1 for r in results if r["status"] == "error"),
        "results": results,
    }
    audit("bulk_provision", f"{len(req.oprids)} oprids", result)
    return result


def _load_requests() -> dict:
    if not REQUESTS_FILE.exists():
        return {}
    try:
        return json.loads(REQUESTS_FILE.read_text()) or {}
    except Exception:
        return {}


def _save_requests(data: dict) -> None:
    REQUESTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    REQUESTS_FILE.write_text(json.dumps(data, indent=2))


@router.get("/requests")
def list_provision_requests(status: str = ""):
    data = _load_requests()
    items = list(data.values())
    if status:
        items = [r for r in items if r.get("status") == status]
    return sorted(items, key=lambda r: r.get("created_at", ""), reverse=True)


@router.post("/requests")
def create_provision_request(req: ProvisionRequestCreate, env: str = psdb.default_env()):
    oprid = req.oprid.strip().upper()

    ps_user = psdb.oprid(oprid, env)
    if not ps_user:
        return {"status": "error", "message": f"OPRID {oprid} not found in PeopleSoft"}

    auth = authelia_admin.load_db()
    if oprid in auth["users"]:
        return {"status": "error", "message": f"{oprid} is already provisioned in Authelia"}

    data = _load_requests()
    for existing in data.values():
        if existing.get("oprid") == oprid and existing.get("status") == "pending":
            return {"status": "error", "message": f"Pending request already exists for {oprid}"}

    req_id = secrets.token_hex(8)
    now = datetime.now(timezone.utc).isoformat()
    data[req_id] = {
        "id": req_id,
        "oprid": oprid,
        "reason": req.reason,
        "requested_by": req.requested_by,
        "status": "pending",
        "created_at": now,
        "reviewed_at": None,
        "reviewed_by": None,
        "reject_reason": None,
        "ps_displayname": ps_user.get("oprdefndesc") or oprid,
    }
    _save_requests(data)
    audit("request_provision", oprid, {"request_id": req_id, "reason": req.reason})
    return {"status": "created", "id": req_id}


@router.post("/requests/{req_id}/approve")
def approve_provision_request(req_id: str, env: str = psdb.default_env()):
    data = _load_requests()
    if req_id not in data:
        raise HTTPException(status_code=404, detail="Request not found")
    entry = data[req_id]
    if entry["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Request is already {entry['status']}")

    oprid = entry["oprid"]
    comparison = compare_identity(oprid, env)
    if not comparison["peoplesoft"]:
        raise HTTPException(status_code=422, detail="PeopleSoft OPRID no longer found")

    now = datetime.now(timezone.utc).isoformat()

    if comparison["authelia_exists"]:
        entry.update({"status": "approved", "reviewed_at": now, "reviewed_by": "admin", "note": "Already existed"})
        _save_requests(data)
        return {"status": "approved", "oprid": oprid, "note": "User already existed in Authelia"}

    password = _gen_password()
    auth = authelia_admin.load_db()
    auth["users"][oprid] = {
        "disabled": comparison["peoplesoft"].get("acctlock") != 0,
        "displayname": comparison["peoplesoft"].get("oprdefndesc") or oprid,
        "password": argon2.hash(password),
        "email": f"{oprid.lower()}@deathstar.chickenkiller.com",
        "groups": comparison["mapped_groups"],
    }
    authelia_admin.save_db(auth)

    entry.update({"status": "approved", "reviewed_at": now, "reviewed_by": "admin", "temp_password": password})
    _save_requests(data)

    result = {"status": "approved", "oprid": oprid, "temp_password": password, "groups": comparison["mapped_groups"]}
    audit("approve_provision_request", oprid, {"request_id": req_id, **result})
    return result


@router.post("/requests/{req_id}/reject")
def reject_provision_request(req_id: str, req: ProvisionRequestReject):
    data = _load_requests()
    if req_id not in data:
        raise HTTPException(status_code=404, detail="Request not found")
    entry = data[req_id]
    if entry["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Request is already {entry['status']}")

    now = datetime.now(timezone.utc).isoformat()
    entry.update({"status": "rejected", "reviewed_at": now, "reviewed_by": "admin", "reject_reason": req.reason})
    _save_requests(data)

    audit("reject_provision_request", entry["oprid"], {"request_id": req_id, "reason": req.reason})
    return {"status": "rejected", "id": req_id}


@router.delete("/requests/{req_id}")
def cancel_provision_request(req_id: str):
    data = _load_requests()
    if req_id not in data:
        raise HTTPException(status_code=404, detail="Request not found")
    if data[req_id]["status"] != "pending":
        raise HTTPException(status_code=409, detail="Only pending requests can be cancelled")
    oprid = data[req_id]["oprid"]
    del data[req_id]
    _save_requests(data)
    audit("cancel_provision_request", oprid, {"request_id": req_id})
    return {"status": "cancelled", "id": req_id}


@router.get("/status")
def identity_status(env: str = psdb.default_env()):
    data = authelia_admin.load_db()
    results = []

    for username, user in data["users"].items():
        try:
            c = compare_identity(username, env)

            ps_exists = c["peoplesoft"] is not None
            expected_groups = set(c["mapped_groups"])
            actual_groups = set(user.get("groups", []))

            in_sync = (
                ps_exists
                and expected_groups == actual_groups
                and user.get("disabled", False) == (c["peoplesoft"].get("acctlock") != 0)
            )

            results.append({
                "username": username,
                "peoplesoft_exists": ps_exists,
                "authelia_exists": True,
                "in_sync": in_sync,
                "expected_groups": sorted(expected_groups),
                "actual_groups": sorted(actual_groups),
                "missing_groups": sorted(expected_groups - actual_groups),
                "extra_groups": sorted(actual_groups - expected_groups),
            })
        except Exception as exc:
            results.append({
                "username": username,
                "error": str(exc),
                "in_sync": False,
            })

    return results


@router.post("/sync-all")
def sync_all_identities(env: str = psdb.default_env()):
    data = authelia_admin.load_db()
    results = []

    for username in list(data["users"].keys()):
        try:
            result = sync_identity(username, env)
            results.append({
                "username": username,
                "result": result
            })
        except Exception as exc:
            results.append({
                "username": username,
                "status": "error",
                "error": str(exc)
            })

    result = {
        "status": "complete",
        "count": len(results),
        "results": results
    }

    audit("sync_all_identities", "all", result)
    return result


@router.get("/audit")
def identity_audit(limit: int = 100):
    if not AUDIT_FILE.exists():
        return []

    lines = AUDIT_FILE.read_text().splitlines()[-limit:]
    return [json.loads(line) for line in lines]



