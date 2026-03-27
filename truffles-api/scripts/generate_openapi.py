import argparse
import os
import sys

import yaml
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

# Add the parent directory to sys.path to allow importing app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routers import calendar, console


def _extract_methods(spec: dict) -> set[tuple[str, str]]:
    methods: set[tuple[str, str]] = set()
    paths = spec.get("paths") or {}
    base_prefix = ""
    servers = spec.get("servers") or []
    if servers and isinstance(servers, list) and isinstance(servers[0], dict):
        url = str(servers[0].get("url", "")).strip()
        if url.startswith("/"):
            base_prefix = url.rstrip("/")
    for path, operations in paths.items():
        if not isinstance(operations, dict):
            continue
        normalized_path = str(path)
        if base_prefix and not normalized_path.startswith(base_prefix):
            normalized_path = f"{base_prefix}{normalized_path}"
        for method in operations.keys():
            if not isinstance(method, str):
                continue
            normalized = method.lower()
            if normalized in {"get", "post", "put", "patch", "delete", "options", "head"}:
                methods.add((normalized_path, normalized))
    return methods


def _build_app(canonical_info: dict) -> FastAPI:
    app = FastAPI(
        title=canonical_info.get("title", "Truffles Console API"),
        version=str(canonical_info.get("version", "1.0.0")),
        description=canonical_info.get("description", ""),
    )
    app.include_router(console.router)
    # Mirror production wiring for contract drift checks.
    app.include_router(calendar.router, prefix="/console/v1")
    return app


def _strip_query_nullability(schema: dict) -> None:
    paths = schema.get("paths") or {}
    if not isinstance(paths, dict):
        return

    def _normalize_parameter(parameter: dict) -> None:
        if not isinstance(parameter, dict):
            return
        if parameter.get("in") != "query":
            return
        param_schema = parameter.get("schema")
        if not isinstance(param_schema, dict):
            return
        any_of = param_schema.get("anyOf")
        if not isinstance(any_of, list):
            return
        non_null_variants = [
            item
            for item in any_of
            if not (isinstance(item, dict) and item.get("type") == "null")
        ]
        if len(non_null_variants) != 1 or len(non_null_variants) == len(any_of):
            return
        replacement = dict(non_null_variants[0])
        for key, value in param_schema.items():
            if key == "anyOf" or key in replacement:
                continue
            replacement[key] = value
        parameter["schema"] = replacement

    def _normalize_parameters(parameters: object) -> None:
        if not isinstance(parameters, list):
            return
        for parameter in parameters:
            _normalize_parameter(parameter)

    for path_item in paths.values():
        if not isinstance(path_item, dict):
            continue
        _normalize_parameters(path_item.get("parameters"))
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            _normalize_parameters(operation.get("parameters"))


def generate_openapi(canonical_info: dict) -> dict:
    app = _build_app(canonical_info)
    schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )
    _strip_query_nullability(schema)
    return schema


def _write_openapi(schema: dict, output_file: str) -> None:
    with open(output_file, "w") as f:
        yaml.dump(schema, f, sort_keys=False)


def _load_yaml(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def _check_drift(generated: dict, canonical: dict) -> None:
    generated_methods = _extract_methods(generated)
    canonical_methods = _extract_methods(canonical)
    missing_in_contract = sorted(generated_methods - canonical_methods)
    missing_in_code = sorted(canonical_methods - generated_methods)

    if missing_in_contract or missing_in_code:
        if missing_in_contract:
            print("Missing in contract:")
            for path, method in missing_in_contract:
                print(f"  {method.upper()} {path}")
        if missing_in_code:
            print("Missing in code:")
            for path, method in missing_in_code:
                print(f"  {method.upper()} {path}")
        raise SystemExit("OpenAPI contract drift detected")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Console OpenAPI spec")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if contract paths/methods drift from code",
    )
    args = parser.parse_args()

    app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repo_root = os.path.dirname(app_root)
    output_dir = os.path.join(repo_root, "contracts", "console_api")
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, "openapi.generated.yaml")
    canonical_file = os.path.join(output_dir, "openapi.v1.yaml")

    canonical = _load_yaml(canonical_file)
    canonical_info = canonical.get("info") if isinstance(canonical, dict) else {}
    schema = generate_openapi(canonical_info if isinstance(canonical_info, dict) else {})
    _write_openapi(schema, output_file)
    print(f"OpenAPI specification generated at: {output_file}")

    if args.check:
        _check_drift(schema, canonical)


if __name__ == "__main__":
    main()
