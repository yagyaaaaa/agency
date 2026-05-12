"""Revenue-focused agent workflows for QuantumReach Agency OS."""
from __future__ import annotations

from src.agents.cold_email import ColdEmailAgent, render_initial_email
from src.agents.content import ContentAgent, build_content_pack
from src.agents.followup import FollowupAgent, is_followup_eligible_status
from src.agents.package_recommendation import recommend_package
from src.agents.scoring import LeadScore, score_lead

__all__ = [
    "ColdEmailAgent",
    "ContentAgent",
    "FollowupAgent",
    "LeadScore",
    "build_content_pack",
    "is_followup_eligible_status",
    "recommend_package",
    "render_initial_email",
    "score_lead",
]
