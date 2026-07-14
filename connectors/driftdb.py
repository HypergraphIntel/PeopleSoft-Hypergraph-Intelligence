"""
Drift database — SQLite-backed store for scheduled envcompare summary snapshots.
Records per-object-type count history and surfaces alerts when drift grows.
"""

import json
import sqlite3
import time
from pathlib import Path

DATA_DIR = Path("/opt/deathstar-api/data")
DB_PATH = DATA_DIR / "drift.db"

# Alert when absolute delta exceeds this many objects
ALERT_THRESHOLD = 50
# Alert when delta grows by this fraction from the previous snapshot
ALERT_GROWTH_RATE = 0.10   # 10%


def _conn():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS drift_snapshots (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                env1        TEXT NOT NULL,
                env2        TEXT NOT NULL,
                snapped_at  TEXT NOT NULL,
                counts_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_drift_snap
                ON drift_snapshots(env1, env2, snapped_at DESC);

            CREATE TABLE IF NOT EXISTS drift_alerts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                env1         TEXT NOT NULL,
                env2         TEXT NOT NULL,
                object_type  TEXT NOT NULL,
                alert_type   TEXT NOT NULL,
                delta        INTEGER,
                prev_delta   INTEGER,
                message      TEXT NOT NULL,
                first_seen   TEXT NOT NULL,
                last_seen    TEXT NOT NULL,
                resolved_at  TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_drift_alert
                ON drift_alerts(env1, env2, resolved_at, last_seen DESC);
        """)


def _now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def record_summary(env1: str, env2: str, counts: list) -> dict:
    """
    Persist an envcompare summary snapshot and generate alerts on significant changes.
    `counts` is the list of {type, env1_count, env2_count, delta} dicts from
    envcompare.summary().
    Returns {snapshot_id, alerts_created}.
    """
    init_db()
    now = _now_iso()
    counts_json = json.dumps(counts)

    with _conn() as con:
        cur = con.execute(
            "INSERT INTO drift_snapshots(env1, env2, snapped_at, counts_json) VALUES(?,?,?,?)",
            (env1, env2, now, counts_json),
        )
        snap_id = cur.lastrowid

    alerts_created = _check_alerts(env1, env2, counts, now)
    return {"snapshot_id": snap_id, "alerts_created": alerts_created, "snapped_at": now}


def _check_alerts(env1: str, env2: str, new_counts: list, now: str) -> int:
    """Compare new counts to the previous snapshot and upsert alerts."""
    prev = get_latest(env1, env2, before=now)
    prev_map = {r["type"]: r for r in (prev or [])}
    created = 0

    with _conn() as con:
        for row in new_counts:
            otype = row.get("type", "")
            delta = row.get("delta")
            if delta is None:
                continue
            abs_delta = abs(delta)
            prev_row = prev_map.get(otype)
            prev_delta = prev_row["delta"] if prev_row and prev_row.get("delta") is not None else None

            alert_type = None
            message = None

            # Alert: delta exceeds threshold
            if abs_delta >= ALERT_THRESHOLD:
                alert_type = "threshold"
                message = (f"{otype}: delta={delta:+d} ({env1}={row.get('env1_count')} "
                           f"vs {env2}={row.get('env2_count')}) exceeds threshold of {ALERT_THRESHOLD}")

            # Alert: delta grew meaningfully since last snapshot
            elif (prev_delta is not None and abs(prev_delta) > 0 and
                  abs_delta > abs(prev_delta) * (1 + ALERT_GROWTH_RATE)):
                alert_type = "delta_grew"
                message = (f"{otype}: delta grew from {prev_delta:+d} to {delta:+d} "
                           f"— environments diverging")

            if not alert_type:
                # Auto-resolve any existing alert for this type if delta is small
                con.execute("""
                    UPDATE drift_alerts
                       SET resolved_at = ?
                     WHERE env1=? AND env2=? AND object_type=? AND resolved_at IS NULL
                """, (now, env1, env2, otype))
                continue

            # Upsert: extend last_seen on existing open alert; else insert
            existing = con.execute("""
                SELECT id FROM drift_alerts
                 WHERE env1=? AND env2=? AND object_type=? AND alert_type=? AND resolved_at IS NULL
            """, (env1, env2, otype, alert_type)).fetchone()

            if existing:
                con.execute("""
                    UPDATE drift_alerts
                       SET last_seen=?, delta=?, prev_delta=?, message=?
                     WHERE id=?
                """, (now, delta, prev_delta, message, existing["id"]))
            else:
                con.execute("""
                    INSERT INTO drift_alerts
                        (env1, env2, object_type, alert_type, delta, prev_delta,
                         message, first_seen, last_seen)
                    VALUES(?,?,?,?,?,?,?,?,?)
                """, (env1, env2, otype, alert_type, delta, prev_delta,
                      message, now, now))
                created += 1

    return created


def get_latest(env1: str, env2: str, before: str = None) -> list:
    """Return the count rows from the most recent snapshot (optionally before a given ISO timestamp)."""
    init_db()
    with _conn() as con:
        if before:
            row = con.execute("""
                SELECT counts_json FROM drift_snapshots
                 WHERE env1=? AND env2=? AND snapped_at < ?
                 ORDER BY snapped_at DESC LIMIT 1
            """, (env1, env2, before)).fetchone()
        else:
            row = con.execute("""
                SELECT counts_json FROM drift_snapshots
                 WHERE env1=? AND env2=?
                 ORDER BY snapped_at DESC LIMIT 1
            """, (env1, env2)).fetchone()
    return json.loads(row["counts_json"]) if row else []


def get_history(env1: str, env2: str, days: int = 30) -> dict:
    """
    Return time-series data for the past `days` days.
    Result: {snapped_at: [count_rows], ...} ordered chronologically,
    plus a `series` dict keyed by object_type → list of {t, delta, env1_count, env2_count}.
    """
    init_db()
    cutoff = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                           time.gmtime(time.time() - days * 86400))
    with _conn() as con:
        rows = con.execute("""
            SELECT id, snapped_at, counts_json FROM drift_snapshots
             WHERE env1=? AND env2=? AND snapped_at >= ?
             ORDER BY snapped_at ASC
        """, (env1, env2, cutoff)).fetchall()

    snapshots = []
    series: dict = {}
    for row in rows:
        t = row["snapped_at"]
        counts = json.loads(row["counts_json"])
        snapshots.append({"id": row["id"], "snapped_at": t, "counts": counts})
        for c in counts:
            otype = c.get("type", "")
            series.setdefault(otype, []).append({
                "t": t,
                "delta": c.get("delta"),
                "env1_count": c.get("env1_count"),
                "env2_count": c.get("env2_count"),
            })

    return {
        "env1": env1, "env2": env2,
        "days": days,
        "snapshot_count": len(snapshots),
        "snapshots": snapshots,
        "series": series,
    }


def get_alerts(env1: str, env2: str, include_resolved: bool = False) -> list:
    """Return current alerts, optionally including resolved ones."""
    init_db()
    with _conn() as con:
        if include_resolved:
            rows = con.execute("""
                SELECT * FROM drift_alerts
                 WHERE env1=? AND env2=?
                 ORDER BY last_seen DESC LIMIT 200
            """, (env1, env2)).fetchall()
        else:
            rows = con.execute("""
                SELECT * FROM drift_alerts
                 WHERE env1=? AND env2=? AND resolved_at IS NULL
                 ORDER BY last_seen DESC
            """, (env1, env2)).fetchall()
    return [dict(r) for r in rows]


def snapshot_count(env1: str, env2: str) -> int:
    """Return total number of stored snapshots for this env pair."""
    init_db()
    with _conn() as con:
        row = con.execute(
            "SELECT COUNT(*) AS n FROM drift_snapshots WHERE env1=? AND env2=?",
            (env1, env2),
        ).fetchone()
    return row["n"] if row else 0


def delete_snapshot(snapshot_id: int) -> bool:
    """Delete a single drift snapshot by id. Returns True if a row was deleted."""
    init_db()
    with _conn() as con:
        cur = con.execute("DELETE FROM drift_snapshots WHERE id=?", (snapshot_id,))
        return cur.rowcount > 0


def prune(env1: str, env2: str, keep: int = 90) -> int:
    """Delete oldest snapshots beyond `keep` count. Returns rows deleted."""
    init_db()
    with _conn() as con:
        total = con.execute(
            "SELECT COUNT(*) AS n FROM drift_snapshots WHERE env1=? AND env2=?",
            (env1, env2),
        ).fetchone()["n"]
        if total <= keep:
            return 0
        cutoff_row = con.execute("""
            SELECT snapped_at FROM drift_snapshots
             WHERE env1=? AND env2=?
             ORDER BY snapped_at DESC LIMIT 1 OFFSET ?
        """, (env1, env2, keep - 1)).fetchone()
        if not cutoff_row:
            return 0
        cur = con.execute("""
            DELETE FROM drift_snapshots
             WHERE env1=? AND env2=? AND snapped_at < ?
        """, (env1, env2, cutoff_row["snapped_at"]))
        return cur.rowcount
