"""Shared scorecard schema for DifficultAI.

All dimensions are expected to be scored on a 1-10 scale (floats allowed),
where higher is better.
"""

SCORECARD_DIMENSIONS = (
    "clarity",
    "confidence",
    "commitment",
    "adaptability",
    "composure",
    "effectiveness",
)
