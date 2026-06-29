"""SQLite state DB for the banking app rebuild runner.

Tracks every recipe call's lifecycle: pending → running → succeeded/failed.
On crash + resume, the orchestrator queries this DB to skip already-completed
recipes + restart in-progress or failed ones.

Schema is intentionally simple — one row per recipe call. The (app, recipe_kind,
target_name) tuple is unique. Phases are derived columns (sortable strings).

Usage:
    db = StateDB(Path('builds/home_banking/runner_state.db'))
    db.upsert_pending(app='core', phase='02_static', target='ChartDataOption', prompt_path=...)
    db.mark_running(row_id)
    db.mark_succeeded(row_id, stdout='Recipe 02: ... | Status: OK')
    pending = db.list_pending(app='core')
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ─── Schema ────────────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS recipe_calls (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    app             TEXT NOT NULL,             -- 'core', 'portal', 'backoffice', ...
    phase           TEXT NOT NULL,             -- '01_server', '02_static', '03_role', '04_serveraction', ...
    target_name     TEXT NOT NULL,             -- entity/role/action name
    prompt_path     TEXT NOT NULL,             -- path to the rendered .prompt.txt
    status          TEXT NOT NULL DEFAULT 'pending',
                    -- 'pending' | 'running' | 'succeeded' | 'failed' | 'skipped'
    run_id          TEXT,                      -- Mentor run id (set on running)
    session_id      TEXT,                      -- Mentor session id (set on succeeded)
    session_token   TEXT,                      -- refreshed token (set on succeeded)
    stdout          TEXT,                      -- captured stdoutOutput on success
    error           TEXT,                      -- error message on failure
    retries         INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    UNIQUE(app, phase, target_name)
);

CREATE INDEX IF NOT EXISTS idx_status_app_phase ON recipe_calls(app, phase, status);

CREATE TABLE IF NOT EXISTS gates (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    app             TEXT NOT NULL,
    gate_kind       TEXT NOT NULL,             -- 'portal_create', 'studio_warmup', 'manage_deps', 'publish'
    description     TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',    -- 'pending' | 'satisfied'
    satisfied_at    TEXT,
    created_at      TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class RecipeCall:
    """One row from recipe_calls. Use this for orchestrator dispatch."""
    id: int
    app: str
    phase: str
    target_name: str
    prompt_path: str
    status: str
    run_id: Optional[str]
    session_id: Optional[str]
    session_token: Optional[str]
    stdout: Optional[str]
    error: Optional[str]
    retries: int
    created_at: str
    updated_at: str


class StateDB:
    """Thin wrapper over sqlite3. NOT thread-safe — one connection per phase
    coordinator. Parallel dispatch should serialize writes through one StateDB
    instance via an asyncio.Lock or similar."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)

    def close(self) -> None:
        self.conn.close()

    # ─── Recipe calls ─────────────────────────────────────────────────────────

    def upsert_pending(self, app: str, phase: str, target_name: str, prompt_path: str) -> int:
        """Add a recipe call as pending. If it already exists in a non-terminal
        state, leave it alone. Returns row id."""
        now = _now()
        existing = self.conn.execute(
            "SELECT id, status FROM recipe_calls WHERE app=? AND phase=? AND target_name=?",
            (app, phase, target_name),
        ).fetchone()
        if existing:
            return existing["id"]
        cur = self.conn.execute(
            """
            INSERT INTO recipe_calls (app, phase, target_name, prompt_path, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'pending', ?, ?)
            """,
            (app, phase, target_name, prompt_path, now, now),
        )
        return cur.lastrowid

    def mark_running(self, row_id: int, run_id: str) -> None:
        self.conn.execute(
            "UPDATE recipe_calls SET status='running', run_id=?, updated_at=? WHERE id=?",
            (run_id, _now(), row_id),
        )

    def mark_succeeded(
        self,
        row_id: int,
        stdout: str,
        session_id: Optional[str] = None,
        session_token: Optional[str] = None,
    ) -> None:
        self.conn.execute(
            """
            UPDATE recipe_calls
            SET status='succeeded', stdout=?, session_id=?, session_token=?, error=NULL, updated_at=?
            WHERE id=?
            """,
            (stdout, session_id, session_token, _now(), row_id),
        )

    def mark_failed(self, row_id: int, error: str) -> None:
        self.conn.execute(
            """
            UPDATE recipe_calls
            SET status='failed', error=?, retries=retries + 1, updated_at=?
            WHERE id=?
            """,
            (error, _now(), row_id),
        )

    def list_by_status(self, app: str, status: str, phase: Optional[str] = None) -> list[RecipeCall]:
        if phase:
            rows = self.conn.execute(
                "SELECT * FROM recipe_calls WHERE app=? AND status=? AND phase=? ORDER BY id",
                (app, status, phase),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM recipe_calls WHERE app=? AND status=? ORDER BY id",
                (app, status),
            ).fetchall()
        return [self._row_to_call(r) for r in rows]

    def list_pending(self, app: str, phase: Optional[str] = None) -> list[RecipeCall]:
        return self.list_by_status(app, "pending", phase)

    def counts(self, app: str) -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT status, COUNT(*) AS n FROM recipe_calls WHERE app=? GROUP BY status",
            (app,),
        ).fetchall()
        return {r["status"]: r["n"] for r in rows}

    @staticmethod
    def _row_to_call(r: sqlite3.Row) -> RecipeCall:
        return RecipeCall(
            id=r["id"],
            app=r["app"],
            phase=r["phase"],
            target_name=r["target_name"],
            prompt_path=r["prompt_path"],
            status=r["status"],
            run_id=r["run_id"],
            session_id=r["session_id"],
            session_token=r["session_token"],
            stdout=r["stdout"],
            error=r["error"],
            retries=r["retries"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )

    # ─── Gates ────────────────────────────────────────────────────────────────

    def add_gate(self, app: str, gate_kind: str, description: str) -> int:
        existing = self.conn.execute(
            "SELECT id FROM gates WHERE app=? AND gate_kind=?", (app, gate_kind)
        ).fetchone()
        if existing:
            return existing["id"]
        cur = self.conn.execute(
            "INSERT INTO gates (app, gate_kind, description, created_at) VALUES (?, ?, ?, ?)",
            (app, gate_kind, description, _now()),
        )
        return cur.lastrowid

    def satisfy_gate(self, gate_id: int) -> None:
        self.conn.execute(
            "UPDATE gates SET status='satisfied', satisfied_at=? WHERE id=?",
            (_now(), gate_id),
        )

    def list_pending_gates(self, app: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM gates WHERE app=? AND status='pending' ORDER BY id", (app,)
        ).fetchall()
        return [dict(r) for r in rows]
