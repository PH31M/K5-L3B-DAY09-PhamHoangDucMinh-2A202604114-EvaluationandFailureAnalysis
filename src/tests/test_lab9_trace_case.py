"""Regression test for the trace case in docs/trace_case.md: seeded_regression C-002@11 (FM-03 ticket_trust).

Runs the real shapes (MockLLM, fresh temp store) and grades the Trial with the Lab 9 graders.
It fails on the buggy variant and passes on `fixed`.
"""
import pytest

pytestmark = pytest.mark.student
CLAIM, SEED = "C-002", 11


@pytest.fixture(scope="module")
def case():
    from lab9.trace_case import investigate

    return {shape: investigate(shape, CLAIM, SEED) for shape in ("seeded_regression", "fixed")}


def grade(grader_cls, case_):
    from pydantic_evals.evaluators import EvaluatorContext

    ctx = EvaluatorContext(name="t", inputs={}, metadata=None, expected_output=case_["label"], output=case_["trial"],
                           duration=0.0, _span_tree=None, attributes={}, metrics={})
    return grader_cls().evaluate(ctx).value


def test_first_wrong_step_is_the_ticket_override(case):
    events = case["seeded_regression"]["trial"]["events"]
    kinds = [e["kind"] for e in events]
    first = kinds.index("model_override")
    assert first == 2                                           # event 3: right after the investigator
    assert events[first - 1]["payload"]["lookup_order"]["order"]["delay_days"] == 2   # the DB said 2 days
    assert events[first]["payload"]["delay_days"] == 5          # the ticket said 5; the agent took the ticket


def test_graders_flag_the_buggy_variant(case):
    from lab9 import graders

    bad = case["seeded_regression"]
    assert grade(graders.DbFactKept, bad) is False             # step level: the override event
    assert grade(graders.RefundAmountCorrect, bad) is False    # outcome level: 20.000đ booked, label 0
    assert bad["trial"]["lab8_pass"] is False


def test_fixed_passes_the_same_claim(case):
    from lab9 import graders

    good = case["fixed"]
    assert "model_override" not in [e["kind"] for e in good["trial"]["events"]]
    assert grade(graders.DbFactKept, good) is True
    assert grade(graders.RefundAmountCorrect, good) is True
    assert grade(graders.ReplyMatchesLedger, good) is True
    assert good["trial"]["lab8_pass"] is True
