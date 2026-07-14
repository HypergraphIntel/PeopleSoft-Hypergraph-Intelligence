"""
Single source of truth for where the application reads its config and
writes its data/logs.

Every module that reads config.json, or writes to data/ or logs/, used to
hardcode the absolute path "/opt/deathstar-api" directly — correct for the
one production host this app had run on before containerization, but it
meant the app could never be imported (let alone run) anywhere else: a
fresh checkout in CI, a developer's laptop, or a container all break
identically, since nothing computes these paths — they were just repeated
as literals across 19 files.

Two independent concerns, both resolved here:

1. APP_ROOT — the repo root itself (source code, static assets, plugins/),
   resolved from this file's own location by default so production
   behavior on the bare-metal host is unchanged (this file still lives at
   /opt/deathstar-api/connectors/paths.py there). DEATHSTAR_HOME overrides
   it wholesale (used by CI to point at the checkout directory).

2. CONFIG_FILE / DATA_DIR / LOG_DIR — where config.json lives and where
   data/logs get written, each independently overridable. In the
   container image (see Dockerfile/compose.yml) these are intentionally
   NOT under APP_ROOT: config.json is a separate read-only secret mount
   (PHI_CONFIG_FILE=/config/config.json), while data/ and logs/ are
   separate writable volumes (PHI_DATA_DIR=/app/data,
   PHI_LOG_DIR=/app/logs) — keeping secrets and mutable state out of the
   application image entirely, standard container practice. Outside a
   container (bare metal, CI), all three default to their historical
   locations directly under APP_ROOT, so nothing changes unless the env
   vars are actually set.

config/role_mapping.yml is NOT part of CONFIG_FILE's scope — it's static,
non-secret config shipped inside the image alongside the source code, not
something that needs its own external mount, so it stays APP_ROOT-relative.
"""

import os
from pathlib import Path

APP_ROOT = Path(os.environ.get("DEATHSTAR_HOME", Path(__file__).resolve().parent.parent))

CONFIG_FILE = Path(os.environ.get("PHI_CONFIG_FILE", APP_ROOT / "config.json"))
DATA_DIR = Path(os.environ.get("PHI_DATA_DIR", APP_ROOT / "data"))
LOG_DIR = Path(os.environ.get("PHI_LOG_DIR", APP_ROOT / "logs"))
