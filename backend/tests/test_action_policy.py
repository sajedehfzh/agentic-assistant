"""Tests for proposed-action approval state transitions."""

from __future__ import annotations

import pytest

from app.models.proposed_action import ProposedActionStatus
from app.services.action_policy import validate_action_transition


def test_proposed_actions_can_be_approved_rejected_or_edited() -> None:
    validate_action_transition(ProposedActionStatus.PROPOSED, "approve")
    validate_action_transition(ProposedActionStatus.PROPOSED, "reject")
    validate_action_transition(ProposedActionStatus.PROPOSED, "edit")


def test_executed_actions_are_locked() -> None:
    with pytest.raises(ValueError, match="Cannot approve"):
        validate_action_transition(ProposedActionStatus.EXECUTED, "approve")
    with pytest.raises(ValueError, match="Cannot edit"):
        validate_action_transition(ProposedActionStatus.EXECUTED, "edit")


def test_failed_actions_can_be_retried() -> None:
    validate_action_transition(ProposedActionStatus.FAILED, "retry")

    with pytest.raises(ValueError, match="Cannot retry"):
        validate_action_transition(ProposedActionStatus.PROPOSED, "retry")
