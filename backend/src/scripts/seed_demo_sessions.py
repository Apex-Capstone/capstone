"""Seed completed demo sessions from generated_validation_cases fixtures.

Loads fixtures, inserts Session + Turn rows (no DialogueService, no patient LLM), then runs
ScoringService.generate_feedback (hybrid when frozen on session / settings).

Usage (from ``backend/`` directory, with ``backend/.env`` loaded):

  PYTHONPATH=src:. python src/scripts/seed_demo_sessions.py src/scripts/demo_seed_mapping.json --dry-run
  PYTHONPATH=src:. python src/scripts/seed_demo_sessions.py src/scripts/demo_seed_mapping.json
  PYTHONPATH=src:. python src/scripts/seed_demo_sessions.py src/scripts/demo_seed_mapping.json --force

From repository root (parent of ``backend/``):

  PYTHONPATH=backend/src:backend python backend/src/scripts/seed_demo_sessions.py backend/src/scripts/demo_seed_mapping.json --dry-run

``PYTHONPATH`` must include ``backend/src`` and the ``backend`` directory (so ``tests.fixtures`` resolves).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import traceback
from datetime import timedelta
from pathlib import Path
from typing import Any

# --- path setup: backend/src + backend (for tests.fixtures) ---
_SCRIPT_DIR = Path(__file__).resolve().parent
_SRC_DIR = _SCRIPT_DIR.parent
_BACKEND_ROOT = _SRC_DIR.parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlalchemy.orm import Session as DBSession

from config.settings import get_settings
from core.plugin_manager import _load_class_from_path
from core.time import utc_now
from db.base import SessionLocal
from domain.entities.case import Case
from domain.entities.session import Session as SessionEntity
from domain.entities.turn import Turn
from domain.entities.user import User
from plugins.load_plugins import load_plugins
from plugins.registry import PluginRegistry
from repositories.case_repo import CaseRepository
from repositories.user_repo import UserRepository
from services.scoring_service import ScoringService

from tests.fixtures.generated_validation_cases import (
    TEST_DIFFICULT_DIAGNOSIS_DECENT,
    TEST_DIFFICULT_DIAGNOSIS_MIXED,
    TEST_DIFFICULT_DIAGNOSIS_STRONG,
    TEST_DIFFICULT_DIAGNOSIS_WEAK,
)
from tests.fixtures.conversation_fixture import (
    TEST_CONVERSATION_BAD,
    TEST_CONVERSATION_MEDIUM,
    TEST_CONVERSATION_GOOD,
)

FIXTURES_BY_NAME: dict[str, dict[str, Any]] = {
    TEST_DIFFICULT_DIAGNOSIS_STRONG["name"]: TEST_DIFFICULT_DIAGNOSIS_STRONG,
    TEST_DIFFICULT_DIAGNOSIS_DECENT["name"]: TEST_DIFFICULT_DIAGNOSIS_DECENT,
    TEST_DIFFICULT_DIAGNOSIS_MIXED["name"]: TEST_DIFFICULT_DIAGNOSIS_MIXED,
    TEST_DIFFICULT_DIAGNOSIS_WEAK["name"]: TEST_DIFFICULT_DIAGNOSIS_WEAK,
    TEST_CONVERSATION_BAD["name"]: TEST_CONVERSATION_BAD,
    TEST_CONVERSATION_MEDIUM["name"]: TEST_CONVERSATION_MEDIUM,
    TEST_CONVERSATION_GOOD["name"]: TEST_CONVERSATION_GOOD,
}

# Written into session metadata for every row this script creates; used to scope deletes to demo seeds only.
DEMO_SEED_SOURCE = "generated_validation_cases"


def _json_field(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value)


def _turn_from_fixture_row(
    row: dict[str, Any],
    *,
    session_id: int,
    owner_user_id: int,
) -> Turn:
    role = row["role"]
    metrics = row.get("metrics_json")
    spans = row.get("spans_json")
    rels = row.get("relations_json")
    return Turn(
        session_id=session_id,
        user_id=owner_user_id if role == "user" else None,
        turn_number=row["turn_number"],
        role=role,
        text=row["text"],
        audio_url=None,
        metrics_json=_json_field(metrics) if metrics is not None else None,
        spans_json=_json_field(spans) if spans is not None else None,
        relations_json=_json_field(rels) if rels is not None else None,
        spikes_stage=row.get("expected_spikes"),
    )


def _parse_session_metadata(raw: str | None) -> dict[str, Any]:
    if not raw or not str(raw).strip():
        return {}
    try:
        out = json.loads(raw)
        return out if isinstance(out, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _is_mapped_demo_seed_session(
    meta: dict[str, Any],
    *,
    seed_key: str,
    fixture_name: str,
) -> bool:
    """True only for rows created by this demo seeding flow (same mapping row).

    Requires matching seed_key plus either canonical seed_source or legacy metadata
    (fixture_name + missing seed_source) from older script versions.
    """
    if meta.get("seed_key") != seed_key:
        return False
    if meta.get("seed_source") == DEMO_SEED_SOURCE:
        return True
    # Legacy: seed_key + fixture_name before seed_source was added
    return meta.get("fixture_name") == fixture_name and meta.get("seed_source") is None


def _sessions_for_user_case(db: DBSession, *, user_id: int, case_id: int) -> list[SessionEntity]:
    return (
        db.query(SessionEntity)
        .filter(SessionEntity.user_id == user_id, SessionEntity.case_id == case_id)
        .order_by(SessionEntity.id.asc())
        .all()
    )


def _find_all_mapped_demo_seed_sessions(
    db: DBSession,
    *,
    user_id: int,
    case_id: int,
    seed_key: str,
    fixture_name: str,
) -> list[SessionEntity]:
    """All demo-seeded sessions for this mapping row (there should be at most one; duplicates are a bug)."""
    out: list[SessionEntity] = []
    for s in _sessions_for_user_case(db, user_id=user_id, case_id=case_id):
        meta = _parse_session_metadata(s.session_metadata)
        if _is_mapped_demo_seed_session(meta, seed_key=seed_key, fixture_name=fixture_name):
            out.append(s)
    return out


def _resolve_frozen_plugins(case: Case, settings: Any) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    """Mirror SessionService.create_session plugin freeze (evaluator, patient model, metrics)."""
    case_eval = getattr(case, "evaluator_plugin", None)
    settings_eval = getattr(settings, "evaluator_plugin", None)
    plugin_name: str | None = (str(case_eval).strip() if case_eval else None) or (
        str(settings_eval).strip() if settings_eval else None
    )

    evaluator_version: str | None = None
    if plugin_name:
        try:
            evaluator_cls = PluginRegistry.get_evaluator(plugin_name)
        except ValueError:
            evaluator_cls = _load_class_from_path(plugin_name)
            PluginRegistry.register_evaluator(plugin_name, evaluator_cls)
        evaluator_version = getattr(evaluator_cls, "version", None)
        plugin_name = getattr(evaluator_cls, "name", plugin_name)
    else:
        plugin_name = None

    case_patient = getattr(case, "patient_model_plugin", None)
    settings_patient = getattr(settings, "patient_model_plugin", None)
    patient_name: str | None = (str(case_patient).strip() if case_patient else None) or (
        str(settings_patient).strip() if settings_patient else None
    )

    patient_model_plugin: str | None = None
    patient_model_version: str | None = None
    if patient_name:
        try:
            model_cls = PluginRegistry.get_patient_model(patient_name)
        except ValueError:
            model_cls = _load_class_from_path(patient_name)
            PluginRegistry.register_patient_model(patient_name, model_cls)
        patient_model_plugin = getattr(model_cls, "name", patient_name)
        patient_model_version = getattr(model_cls, "version", None)

    metrics_list: list[str] = []
    raw_case_metrics = getattr(case, "metrics_plugins", None)
    if isinstance(raw_case_metrics, str) and raw_case_metrics.strip():
        try:
            parsed = json.loads(raw_case_metrics)
            if isinstance(parsed, list):
                metrics_list = [str(x) for x in parsed]
        except (json.JSONDecodeError, TypeError):
            pass
    if not metrics_list:
        metrics_list = list(getattr(settings, "metrics_plugins", []) or [])

    resolved_metrics: list[str] = []
    for name in metrics_list:
        if not name:
            continue
        try:
            metrics_cls = PluginRegistry.get_metrics_plugin(name)
        except ValueError:
            metrics_cls = _load_class_from_path(name)
            PluginRegistry.register_metrics_plugin(name, metrics_cls)
        resolved_metrics.append(getattr(metrics_cls, "name", name))

    metrics_plugins_json: str | None = json.dumps(resolved_metrics) if resolved_metrics else None

    return (
        plugin_name,
        evaluator_version,
        patient_model_plugin,
        patient_model_version,
        metrics_plugins_json,
    )


def load_mapping(path: Path) -> tuple[int, list[dict[str, Any]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    case_id = int(data["case_id"])
    mappings = data["mappings"]
    if not isinstance(mappings, list) or not mappings:
        raise SystemExit("mapping JSON must contain a non-empty 'mappings' array")
    return case_id, mappings


async def seed_one(
    db: DBSession,
    *,
    fixture: dict[str, Any],
    user: User,
    case: Case,
    case_id: int,
    seed_key: str,
    email_optional: str | None,
    dry_run: bool,
    force: bool,
) -> None:
    fixture_name = fixture["name"]
    print(f"\n--- fixture={fixture_name!r} seed_key={seed_key!r} ---")
    print(f"    user id={user.id} email={user.email!r} supabase_auth_id={user.supabase_auth_id}")

    if email_optional is not None and str(user.email).lower() != str(email_optional).strip().lower():
        raise SystemExit(
            f"Email mismatch for user id={user.id}: expected {email_optional!r}, DB has {user.email!r}"
        )

    existing_rows = _find_all_mapped_demo_seed_sessions(
        db, user_id=user.id, case_id=case_id, seed_key=seed_key, fixture_name=fixture_name
    )
    if existing_rows:
        if not force:
            ids = ", ".join(str(s.id) for s in existing_rows)
            print(f"    SKIP: demo seed already exists (session_id(s)={ids})")
            return
        if dry_run:
            ids = ", ".join(str(s.id) for s in existing_rows)
            print(f"    DRY-RUN: would delete demo session(s) session_id(s)={ids} (--force)")
        else:
            for s in existing_rows:
                db.delete(s)
            db.commit()
            ids = ", ".join(str(s.id) for s in existing_rows)
            print(f"    deleted demo session(s) session_id(s)={ids} (--force)")

    settings = get_settings()
    ev, ev_ver, pm, pm_ver, m_json = _resolve_frozen_plugins(case, settings)

    ended = utc_now()
    duration_sec = 600
    started = ended - timedelta(seconds=duration_sec)

    meta = {
        "seed_key": seed_key,
        "seed_source": DEMO_SEED_SOURCE,
        "fixture_name": fixture_name,
    }
    meta_json = json.dumps(meta)

    n_turns = len(fixture["transcript"])
    print(f"    case_id={case_id} turns={n_turns} dry_run={dry_run}")
    print(f"    frozen evaluator_plugin={ev!r} patient_model_plugin={pm!r}")

    if dry_run:
        print("    DRY-RUN: would insert Session(state=completed) + turns + generate_feedback")
        return

    session = SessionEntity(
        user_id=user.id,
        case_id=case_id,
        state="completed",
        current_spikes_stage=None,
        started_at=started,
        ended_at=ended,
        duration_seconds=duration_sec,
        session_metadata=meta_json,
        evaluator_plugin=ev,
        evaluator_version=ev_ver,
        patient_model_plugin=pm,
        patient_model_version=pm_ver,
        metrics_plugins=m_json,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    print(f"    created session_id={session.id}")

    for row in fixture["transcript"]:
        t = _turn_from_fixture_row(row, session_id=session.id, owner_user_id=user.id)
        db.add(t)
    db.commit()

    try:
        scoring = ScoringService(db)
        await scoring.generate_feedback(session.id)
        print(f"    scoring OK (feedback persisted) session_id={session.id}")
    except Exception as e:
        print(f"    scoring FAILED session_id={session.id}: {e}")
        traceback.print_exc()
        raise


async def async_main(mapping_path: Path, dry_run: bool, force: bool) -> None:
    load_plugins()
    case_id, mappings = load_mapping(mapping_path.resolve())
    settings = get_settings()
    _ = settings  # ensure settings load

    db = SessionLocal()
    try:
        case_repo = CaseRepository(db)
        case = case_repo.get_by_id(case_id)
        if case is None:
            raise SystemExit(f"case_id={case_id} not found in database")

        user_repo = UserRepository(db)

        for row in mappings:
            seed_key = row["seed_key"]
            supa = row["supabase_auth_id"]
            fixture_name = row["fixture_name"]
            email_opt = row.get("email")

            fixture = FIXTURES_BY_NAME.get(fixture_name)
            if fixture is None:
                raise SystemExit(
                    f"Unknown fixture_name={fixture_name!r}. "
                    f"Expected one of: {sorted(FIXTURES_BY_NAME.keys())}"
                )

            user = user_repo.get_by_supabase_id(str(supa))
            if user is None:
                raise SystemExit(f"No core.users row for supabase_auth_id={supa!r}")

            await seed_one(
                db,
                fixture=fixture,
                user=user,
                case=case,
                case_id=case_id,
                seed_key=seed_key,
                email_optional=email_opt,
                dry_run=dry_run,
                force=force,
            )
    finally:
        db.close()


def main() -> None:
    p = argparse.ArgumentParser(description="Seed demo sessions from generated_validation_cases fixtures.")
    p.add_argument(
        "mapping_json",
        type=Path,
        help="Path to demo_seed_mapping.json",
    )
    p.add_argument("--dry-run", action="store_true", help="Resolve users/fixtures and print plan; no DB writes.")
    p.add_argument(
        "--force",
        action="store_true",
        help="Delete all demo-seeded sessions for this mapping row (same user/case/seed_key), then re-seed.",
    )
    args = p.parse_args()
    path = args.mapping_json
    if not path.is_file():
        raise SystemExit(f"Mapping file not found: {path}")

    asyncio.run(async_main(path, dry_run=args.dry_run, force=args.force))
    print("\nDone.")


if __name__ == "__main__":
    main()
