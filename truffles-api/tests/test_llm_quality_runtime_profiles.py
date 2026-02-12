import ast
import hashlib
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


def _load_helpers():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    wanted_assignments = {
        "LLM_QUALITY_TIMEOUT_PROFILES",
        "LLM_QUALITY_WAIT_DEFAULTS",
    }
    wanted_functions = {
        "_llm_quality_repo_root",
        "_llm_quality_worktree_namespace",
        "_llm_quality_apply_timeout_profile",
        "_llm_quality_build_default_run_id",
    }
    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if names & wanted_assignments:
                selected_nodes.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            selected_nodes.append(node)
    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {
        "__file__": str(script_path),
        "datetime": datetime,
        "timezone": timezone,
        "hashlib": hashlib,
        "os": os,
        "uuid": uuid,
    }
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace


_helpers = _load_helpers()
_apply_profile = _helpers["_llm_quality_apply_timeout_profile"]
_build_run_id = _helpers["_llm_quality_build_default_run_id"]
_worktree_namespace = _helpers["_llm_quality_worktree_namespace"]


def test_profile_applies_realistic_defaults_for_generated_dialogs():
    args = SimpleNamespace(
        timeout_profile="realistic",
        scenarios_file=None,
        timeout=None,
        poll_timeout=None,
        poll_interval=None,
        trace_timeout=None,
        trace_interval=None,
        min_wait=None,
        max_wait=None,
    )

    profiled = _apply_profile(args)

    assert profiled.timeout == 30.0
    assert profiled.poll_timeout == 25.0
    assert profiled.trace_timeout == 25.0
    assert profiled.poll_interval == 0.5
    assert profiled.trace_interval == 0.5
    assert profiled.min_wait == 0.2
    assert profiled.max_wait == 0.4


def test_profile_applies_replay_wait_defaults_for_scenarios_file():
    args = SimpleNamespace(
        timeout_profile="fast-replay",
        scenarios_file="/tmp/booking_quality/seed42/scenarios.json",
        timeout=None,
        poll_timeout=None,
        poll_interval=None,
        trace_timeout=None,
        trace_interval=None,
        min_wait=None,
        max_wait=None,
    )

    profiled = _apply_profile(args)

    assert profiled.timeout == 20.0
    assert profiled.poll_timeout == 16.0
    assert profiled.trace_timeout == 16.0
    assert profiled.min_wait == 0.0
    assert profiled.max_wait == 0.15


def test_profile_keeps_explicit_timeout_overrides():
    args = SimpleNamespace(
        timeout_profile="realistic",
        scenarios_file=None,
        timeout=45.0,
        poll_timeout=33.0,
        poll_interval=0.7,
        trace_timeout=31.0,
        trace_interval=0.8,
        min_wait=0.1,
        max_wait=0.9,
    )

    profiled = _apply_profile(args)

    assert profiled.timeout == 45.0
    assert profiled.poll_timeout == 33.0
    assert profiled.poll_interval == 0.7
    assert profiled.trace_timeout == 31.0
    assert profiled.trace_interval == 0.8
    assert profiled.min_wait == 0.1
    assert profiled.max_wait == 0.9


def test_default_run_id_contains_worktree_namespace_and_pid():
    namespace = _worktree_namespace()
    run_id = _build_run_id("20260212-101010")

    assert run_id.startswith(f"20260212-101010-{namespace}-p")
    assert re.search(r"-p\d+-[0-9a-f]{6}$", run_id)
