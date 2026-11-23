"""Bridge team extraction checks and exported GX results to the shared run log."""

import json


def gx_checks(payload):
    """Accept exported suite results (GX 0.18/1.x); never infer success from zero."""
    results = payload.get("results")
    if not isinstance(results, list) or not results:
        raise ValueError("GX export must contain a nonempty results list")
    checks = []
    for index, result in enumerate(results):
        success = result.get("success")
        if not isinstance(success, bool):
            raise ValueError("GX expectation result has no boolean success")
        config = result.get("expectation_config") or {}
        name = config.get("type") or config.get("expectation_type") or "expectation"
        details = result.get("result") or {}
        exception = result.get("exception_info") or {}
        if exception.get("raised_exception"):
            success = False
        # Row-level counts may be absent, including BOOLEAN_ONLY/aggregate checks.
        # Always log expectation outcomes as 0/1; preserve row counts in details.
        checks.append({"name": f"gx_{index}_{name}", "failed": int(not success), "total": 1,
                       "details": json.dumps({"count_unit": "expectation", "kwargs": config.get("kwargs", {}),
                                              "result": details, "exception_info": exception}, ensure_ascii=False)})
    if payload.get("success") is False and not any(check["failed"] for check in checks):
        checks.append({"name": "gx_suite_failure", "failed": 1, "total": 1,
                       "details": "Suite failed although individual checks did not expose the failure"})
    return checks


def record_team_results(quality, capmas_results, folder):
    for row in capmas_results.itertuples():
        status = str(row.status)
        if status not in {"ok", "review", "failed"}:
            quality.check("capmas_team", "unknown_status", 1, 1, status)
            continue
        details = json.dumps({"count_unit": "table", "source_year": int(row.year),
                              "source_table": int(row.table), "source_rows": int(row.rows),
                              "issues": str(row.issues)}, ensure_ascii=False)
        quality.check("capmas_team", f"table_{row.year}_{row.table}", int(status != "ok"), 1,
                      details, "error" if status == "failed" else "warning")
    for file in sorted(folder.glob("*.json")):
        try:
            checks = gx_checks(json.loads(file.read_text(encoding="utf-8-sig")))
            for check in checks:
                quality.check(f"gx:{file.name}", check["name"], check["failed"], check["total"], check["details"])
        except (ValueError, TypeError, KeyError) as exc:
            quality.check(f"gx:{file.name}", "invalid_validation_export", 1, 1, str(exc))
