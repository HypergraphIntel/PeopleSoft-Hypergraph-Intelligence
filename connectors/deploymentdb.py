"""
Deployment/Configuration History — SQLite-backed store linking promotion events
to a concrete before/after fingerprint of the target environment: a hash of
config.json (detects config-side changes) and the nearest drift snapshot
(detects metadata-side changes), so "what changed" has real evidence attached
to "that something changed" (the promotion log).

Deliberately additive/observational only — no new write capability. Reuses
promotiondb.py's promotion records and driftdb.py's snapshot history rather
than duplicating either.
"""

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from connectors import paths

DATA_DIR = paths.DATA_DIR
DB_PATH = DATA_DIR / "deployment_events.db"
CONFIG_PATH = paths.CONFIG_FILE


def _conn():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS deployment_snapshots (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                promotion_id      INTEGER,
                env               TEXT NOT NULL,
                captured_at       TEXT NOT NULL,
                config_hash       TEXT NOT NULL,
                config_json       TEXT,
                drift_snapshot_id INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_deploy_env
                ON deployment_snapshots(env, captured_at DESC);
            CREATE INDEX IF NOT EXISTS idx_deploy_promo
                ON deployment_snapshots(promotion_id);
        """)


def _now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# Config keys that hold credentials/secrets — never persisted or served, even
# redacted-in-place, since config.json is full of Oracle/SSH/API credentials.
_SECRET_KEYS = {
    "password", "api_key", "apikey", "secret", "salt", "key_path",
    "private_key", "token", "access_key", "secret_key",
}


def _redact(value):
    """Recursively replace secret-keyed values with a fixed placeholder."""
    if isinstance(value, dict):
        return {
            k: ("***REDACTED***" if k.lower() in _SECRET_KEYS and v not in (None, "")
                else _redact(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def _config_hash_and_text():
    """
    Read config.json, redact known secret fields, return (sha256_hex,
    redacted_normalized_text) or (None, None) if unreadable. The hash is
    computed on the redacted form so rotating a credential alone doesn't
    register as a "config changed" event — only structural/non-secret
    changes do.
    """
    try:
        raw = CONFIG_PATH.read_text()
        parsed = json.loads(raw)
        redacted = _redact(parsed)
        normalized = json.dumps(redacted, sort_keys=True)
    except Exception:
        return None, None
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return digest, normalized


def _last_hash_for_env(env: str):
    with _conn() as con:
        row = con.execute("""
            SELECT config_hash FROM deployment_snapshots
             WHERE env=? ORDER BY captured_at DESC LIMIT 1
        """, (env,)).fetchone()
    return row["config_hash"] if row else None


def _nearest_drift_snapshot_id(env: str):
    """
    Find the drift_snapshots row (from driftdb) closest to now involving `env`
    as either side of a comparison pair. Returns None if driftdb has no data
    or the table doesn't exist yet.
    """
    from connectors import driftdb
    driftdb.init_db()
    try:
        with driftdb._conn() as con:
            row = con.execute("""
                SELECT id FROM drift_snapshots
                 WHERE env1=? OR env2=?
                 ORDER BY snapped_at DESC LIMIT 1
            """, (env, env)).fetchone()
    except sqlite3.OperationalError:
        return None
    return row["id"] if row else None


def record_deployment_snapshot(env: str, promotion_id: int = None) -> dict:
    """
    Capture a config-fingerprint snapshot for `env`, optionally tied to a
    promotion event. Only stores the full config_json when the hash changed
    since the last recorded snapshot for this env (dedup, same instinct as
    envcompare's unchanged-content skip) — unless tied to a promotion, in
    which case a row is always recorded (even with an unchanged hash) so
    every promotion has a fingerprint to look back on.
    """
    init_db()
    env = (env or "").upper().strip()
    digest, text = _config_hash_and_text()
    if digest is None:
        return {"recorded": False, "reason": "config.json unreadable"}

    prev_hash = _last_hash_for_env(env)
    changed = digest != prev_hash

    if not changed and promotion_id is None:
        return {"recorded": False, "reason": "config unchanged", "config_hash": digest}

    now = _now_iso()
    drift_id = _nearest_drift_snapshot_id(env)
    with _conn() as con:
        cur = con.execute("""
            INSERT INTO deployment_snapshots
                (promotion_id, env, captured_at, config_hash, config_json, drift_snapshot_id)
            VALUES (?,?,?,?,?,?)
        """, (promotion_id, env, now, digest, text if changed else None, drift_id))
        new_id = cur.lastrowid

    return {
        "recorded": True,
        "id": new_id,
        "env": env,
        "captured_at": now,
        "config_hash": digest,
        "config_changed": changed,
        "drift_snapshot_id": drift_id,
        "promotion_id": promotion_id,
    }


def get_history(env: str, limit: int = 200) -> list:
    """
    Config-fingerprint timeline for an environment, newest first. Rows where
    config_json is present mark an actual configuration-change event; rows
    with only a hash (no config_json) are promotion-tied fingerprints where
    the config happened not to change.
    """
    init_db()
    env = (env or "").upper().strip()
    with _conn() as con:
        rows = con.execute("""
            SELECT id, promotion_id, env, captured_at, config_hash,
                   (config_json IS NOT NULL) AS config_changed, drift_snapshot_id
              FROM deployment_snapshots
             WHERE env=?
             ORDER BY captured_at DESC LIMIT ?
        """, (env, limit)).fetchall()
    return [dict(r) for r in rows]


def get_for_promotion(promotion_id: int) -> dict | None:
    """
    Return the deployment snapshot linked to a specific promotion, including
    the linked promotion record and drift snapshot counts (if any), for the
    "before/after" view of what a promotion actually changed.
    """
    init_db()
    with _conn() as con:
        row = con.execute("""
            SELECT * FROM deployment_snapshots WHERE promotion_id=?
             ORDER BY captured_at DESC LIMIT 1
        """, (promotion_id,)).fetchone()
    if not row:
        return None
    result = dict(row)
    if result.get("config_json"):
        try:
            result["config_json"] = json.loads(result["config_json"])
        except Exception:
            pass

    from connectors import promotiondb
    result["promotion"] = promotiondb.get_promotion(promotion_id)

    if result.get("drift_snapshot_id"):
        from connectors import driftdb
        driftdb.init_db()
        with driftdb._conn() as con:
            drow = con.execute(
                "SELECT * FROM drift_snapshots WHERE id=?",
                (result["drift_snapshot_id"],),
            ).fetchone()
        if drow:
            d = dict(drow)
            d["counts"] = json.loads(d.pop("counts_json"))
            result["drift_snapshot"] = d

    return result


init_db()
