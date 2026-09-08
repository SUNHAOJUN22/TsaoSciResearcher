import argparse
import json

import _bootstrap  # noqa: F401
from tsao_computation.routing import route_question

p = argparse.ArgumentParser()
p.add_argument("question")
a = p.parse_args()
r = route_question(a.question)
print(
    json.dumps(
        {
            "workflow": r.workflow,
            "score": r.score,
            "matched_terms": r.matched_terms,
            "alternatives": r.alternatives,
            "explanation": r.explanation,
        },
        indent=2,
    )
)
