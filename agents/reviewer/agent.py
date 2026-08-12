import os
from typing import Literal

from google.adk.agents import Agent
from pydantic import BaseModel, Field


MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-pro")


# --- Data Models ---
class ReviewFeedback(BaseModel):
    """Structured feedback from the Reviewer agent."""

    status: Literal["pass", "fail"] = Field(
        description="Whether the app is ready to ship ('pass') or needs another build iteration ('fail')."
    )
    feedback: str = Field(
        description="If status is 'fail', a numbered list of concrete defects the builder must fix. If 'pass', a one-line confirmation."
    )


# --- Reviewer Agent ---
# Role: the "QA engineer" of the team. Gates every build against the plan.
reviewer = Agent(
    name="reviewer",
    model=MODEL,
    description="Reviews the built app against the plan and acceptance criteria.",
    instruction="""
    You are a strict staff engineer doing code review and QA.
    Evaluate the app code produced by the builder ('app_code') against the
    team's 'build_plan' and the user's original request.

    The builder emits files as blocks marked `=== FILE: path ===` followed
    by a fenced code block.

    Check, in order:
    1. **Completeness** — is there an `index.html` file containing a full
       HTML document (<!DOCTYPE html> ... </html>)? Does every FILE block
       contain real content (no placeholders, no empty files)?
    2. **Self-contained** — no CDNs, external fonts/images, or network
       calls. Every relative reference (<link href>, <script src>, images)
       must point to a file that was actually emitted.
    3. **Correctness** — read the JavaScript carefully, across all files.
       Flag bugs that would break it at runtime: undefined variables, wrong
       element IDs, event handlers never attached, state that is never
       rendered.
    4. **Acceptance criteria** — does the code plausibly satisfy each
       criterion in the plan?
    5. **Design spec** — if a 'design_spec' exists, does the code follow its
       palette, layout, and interaction details? Flag clear deviations.
    6. **Polish** — usable layout, labeled controls, visible feedback on
       user actions.

    If everything holds, output status='pass'.
    Otherwise output status='fail' with 'feedback' as a numbered list of
    specific, actionable defects (cite the element/function concerned).
    Do not rewrite the code yourself, and do not fail a build for
    nice-to-haves that are outside the plan's MVP scope.
    """,
    output_schema=ReviewFeedback,
    # Disallow transfers as it uses output_schema
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

root_agent = reviewer
