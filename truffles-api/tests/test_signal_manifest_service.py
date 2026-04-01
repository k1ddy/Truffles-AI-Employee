from app.services.signal_manifest_service import (
    get_booking_layout_swap_map,
    get_booking_regex_pattern,
    get_booking_regex_replacements,
    get_booking_text_tokens,
    get_compiled_signal_manifest,
    get_info_regex_pattern,
    get_signal_manifest_runtime_meta,
    load_signal_manifest,
)


def test_signal_manifest_loads_with_expected_schema_version():
    manifest = load_signal_manifest()
    assert manifest.get("schema_version") == "signal_manifest.v1"


def test_signal_manifest_runtime_meta_has_compiled_version_and_fingerprint():
    meta = get_signal_manifest_runtime_meta()
    assert meta["schema_version"] == "signal_manifest.v1"
    assert meta["compiled_version"].startswith("signal_manifest.v1:")
    assert len(meta["manifest_fingerprint"]) == 64
    assert meta["manifest_path"].endswith("SIGNAL_MANIFEST.yaml")


def test_signal_manifest_compiler_cache_reuses_bundle_for_same_signature():
    first = get_compiled_signal_manifest()
    second = get_compiled_signal_manifest()
    assert first is second
    assert first.compiled_version == second.compiled_version


def test_booking_relative_day_patterns_come_from_manifest():
    patterns = get_booking_regex_replacements("relative_day_token_patterns")
    assert patterns

    matched = None
    for pattern, replacement in patterns:
        if pattern.search("можно записаться завтра?"):
            matched = replacement
            break
    assert matched == "завтра"


def test_booking_duration_markers_come_from_manifest():
    markers = get_booking_text_tokens("datetime_duration_context_markers")
    assert "сколько" in markers
    assert "по времени" in markers


def test_booking_layout_swap_map_comes_from_manifest():
    mapping = get_booking_layout_swap_map()
    assert mapping.get("q") == "й"
    assert mapping.get("m") == "ь"


def test_info_tokenize_pattern_comes_from_manifest():
    tokenize_pattern = get_info_regex_pattern("tokenize_word_pattern")
    assert tokenize_pattern is not None
    assert tokenize_pattern.findall("маникюр в 10:30") == ["маникюр", "в", "10", "30"]


def test_booking_hour_pattern_comes_from_manifest():
    pattern = get_booking_regex_pattern("booking_hour_fallback_pattern")
    assert pattern is not None
    match = pattern.search("можно в 16:30")
    assert match is not None
    assert match.group("hour") == "16"
