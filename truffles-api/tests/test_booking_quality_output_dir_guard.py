from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


def _load_module():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    spec = spec_from_file_location("diagnose_script_output_guard", script_path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_module = _load_module()


def test_llm_quality_prepare_output_dir_blocks_non_empty_directory(tmp_path):
    output_dir = tmp_path / "booking-run"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text("{}", encoding="utf-8")

    with pytest.raises(SystemExit, match="output-dir already contains artifacts"):
        _module._llm_quality_prepare_output_dir(str(output_dir), allow_overwrite=False)


def test_llm_quality_prepare_output_dir_cleans_directory_with_allow_overwrite(tmp_path):
    output_dir = tmp_path / "booking-run"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text("{}", encoding="utf-8")
    bundles = output_dir / "failure_bundles"
    bundles.mkdir(parents=True, exist_ok=True)
    (bundles / "trace.log").write_text("trace", encoding="utf-8")

    resolved = _module._llm_quality_prepare_output_dir(str(output_dir), allow_overwrite=True)

    assert resolved == str(output_dir.resolve())
    assert list(output_dir.iterdir()) == []
