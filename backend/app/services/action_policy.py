"""State-transition rules for proposed external actions."""

from __future__ import annotations

from app.models.proposed_action import ProposedActionStatus

EDITABLE_STATUSES = {ProposedActionStatus.PROPOSED, ProposedActionStatus.FAILED}
APPROVABLE_STATUSES = {ProposedActionStatus.PROPOSED, ProposedActionStatus.FAILED}
REJECTABLE_STATUSES = {
    ProposedActionStatus.PROPOSED,
    ProposedActionStatus.APPROVED,
    ProposedActionStatus.FAILED,
}
RETRYABLE_STATUSES = {ProposedActionStatus.FAILED}


def normalize_action_status(status: ProposedActionStatus | str) -> ProposedActionStatus:
    if isinstance(status, ProposedActionStatus):
        return status
    return ProposedActionStatus(status)


def validate_action_transition(status: ProposedActionStatus | str, operation: str) -> None:
    current = normalize_action_status(status)
    allowed_by_operation = {
        "edit": EDITABLE_STATUSES,
        "approve": APPROVABLE_STATUSES,
        "reject": REJECTABLE_STATUSES,
        "retry": RETRYABLE_STATUSES,
    }
    allowed = allowed_by_operation.get(operation)
    if allowed is None:
        raise ValueError(f"Unknown action operation: {operation}")
    if current not in allowed:
        allowed_values = ", ".join(sorted(s.value for s in allowed))
        raise ValueError(
            f"Cannot {operation} an action with status `{current.value}`. "
            f"Allowed statuses: {allowed_values}."
        )
