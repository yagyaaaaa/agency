from src.agents.followup import is_due_followup_allowed, is_followup_eligible_status


def test_followup_blocks_negative_terminal_statuses():
    for status in ["suppressed", "negative_reply", "unsubscribed", "rejected", "converted", "client"]:
        assert not is_followup_eligible_status(status)


def test_followup_allows_new_or_contacted_statuses():
    assert is_followup_eligible_status("new")
    assert is_followup_eligible_status("contacted")


def test_due_followup_blocks_suppression_or_negative_reply():
    lead = {"status": "contacted"}

    assert not is_due_followup_allowed(lead, suppressed=True, negative_reply=False)
    assert not is_due_followup_allowed(lead, suppressed=False, negative_reply=True)
    assert is_due_followup_allowed(lead, suppressed=False, negative_reply=False)
