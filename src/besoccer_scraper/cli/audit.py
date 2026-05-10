from __future__ import annotations


def run_audit(container: object, message: str) -> str:
    return container.audit_use_case.execute(message)
