"""Offline synthetic regression cases; automated checks are not educator approval."""
from copy import deepcopy
from app.modules.decision_engine.recommendation.selection import learning_need, select_recommendations


def candidates():
    def item(id, title, kind="resource", type="image", **fields):
        return dict(id=id, title=title, kind=kind, type=type, version=1,
                    description=title, availability_state="available", **fields)
    return [item("force", "Force push pull", concepts=["force", "push", "pull"]),
        item("gravity", "Falling ball illustration", concepts=["gravity"], synonyms=["things fall"],
             grade_min=0, grade_max=3, languages=["en-in"], purposes=["explain"]),
        item("motion", "Gravity falling ball", type="video", purposes=["demonstrate"]),
        item("kit", "Gravity practice", kind="kit", type="kit", purposes=["practise"]),
        item("tutor", "Science tutor", kind="tutor", type="tutor", topic_expertise=True),
        item("advanced", "Gravity relativity grade 10", grade_min=9, grade_max=12)]


def cases():
    return [dict(name="force", question="Explain force", answer="Force is a push or pull.", expected="force", mode="inline"),
        dict(name="gravity-not-force", question="Explain gravity", answer="Gravity pulls a falling ball down.", expected="gravity", mode="inline"),
        dict(name="synonym", question="Why do things fall?", answer="Gravity pulls objects down.", expected="gravity", mode="inline"),
        dict(name="demonstration", question="Show a gravity video", answer="Gravity makes objects fall.", expected="motion", mode="optional card"),
        dict(name="practice", question="Test my understanding", previous="Explain gravity", answer="Practise gravity.", expected="kit", mode="optional card"),
        dict(name="human", question="I need a tutor", answer="A tutor can help.", expected="tutor", mode="optional card"),
        dict(name="unrelated", question="Explain evaporation", answer="Water becomes gas.", expected=None, mode="none"),
        dict(name="reference", question="Explain force", answer="Force pushes a door.", history=[dict(candidate_id="force", version=1, displayed=True, display_mode="inline", message_id="earlier")], expected="force", mode="reference earlier"),
        dict(name="explicit-repeat", question="Show the force image again", answer="Force pushes a door.", history=[dict(candidate_id="force", version=1, displayed=True, display_mode="inline")], expected="force", mode="inline"),
        dict(name="grade", question="Explain gravity", answer="Gravity pulls objects down.", only=["gravity"], grade="Grade 8", expected=None, mode="none"),
        dict(name="language", question="Explain gravity", answer="Gravity pulls objects down.", only=["gravity"], language="ta", expected=None, mode="none"),
        dict(name="unavailable", question="Explain gravity", answer="Gravity pulls objects down.", only=["gravity"], unavailable=True, expected=None, mode="none")]


def evaluate(*, omit_metadata=False):
    results = []
    for case in cases():
        pool = deepcopy(candidates())
        if case.get("only"):
            pool = [c for c in pool if c["id"] in case["only"]]
        if case.get("unavailable"):
            for c in pool:
                c["availability_state"] = "unavailable"
        if omit_metadata:
            for c in pool:
                for key in ("concepts", "synonyms", "grade_min", "grade_max", "languages", "purposes"):
                    c.pop(key, None)
        need = learning_need(case["question"], case.get("previous", ""))
        if case.get("language"):
            need["language"] = case["language"]
        decision = select_recommendations(pool, need, case["question"], case["answer"],
            grade=case.get("grade", "Grade 1"), history=case.get("history", []))
        primary = decision["primary"]
        actual = primary["candidate_id"] if primary else None
        results.append(dict(case=case["name"], question=case["question"], answer=case["answer"],
            expected=case["expected"], actual=actual, mode=decision["display_mode"],
            passed=actual == case["expected"] and decision["display_mode"] == case["mode"],
            reason=primary["reason"] if primary else "No eligible sufficiently matching candidate.",
            educator_review="pending", educator_notes=""))
    return results
