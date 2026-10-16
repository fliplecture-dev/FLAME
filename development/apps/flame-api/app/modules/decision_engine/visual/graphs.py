"""Graph intent and bounded fallback specifications; never evaluate expressions."""
import re
import math

from app.contracts.math_templates import TEMPLATES

GRAPH_TEMPLATES = frozenset({"coordinate_points", "linear_function", "quadratic_function", "trigonometric_function"})


def graph_requested(question: str) -> bool:
    return bool(re.search(r"\b(?:graphs?|plott?\w*)\b", question, re.I))


def fallback_graph(question: str, template: str | None) -> dict | None:
    """Use a reviewed example or exact supported polynomial, never a guessed equation."""
    if template not in GRAPH_TEMPLATES:
        return None
    parameters = {key: spec["default"] for key, spec in TEMPLATES[template]["parameters"].items()}
    equation = re.search(r"\b(?:y|f\s*\(\s*x\s*\))\s*=\s*([^\n,;?!$]+)", question, re.I)
    description = "Illustrative mathematical example."
    if equation:
        expression = re.split(r"\s+(?:using|with|on|and|explain|please|in|as|for|show|plot|graph)\b", equation[1], maxsplit=1, flags=re.I)[0]
        expression = re.sub(r"\s+", "", expression.lower()).replace("²", "^2").rstrip(".")
        trig = re.fullmatch(r"(sin|cos)\(?x\)?", expression)
        if trig and template == "trigonometric_function":
            parameters["function"] = trig[1]
        elif template in {"linear_function", "quadratic_function"}:
            # A sum of numeric constants, x and x^2 terms is the entire grammar.
            terms = re.findall(r"[+-]?(?:\d+(?:\.\d+)?\*?)?x(?:\^2)?|[+-]?\d+(?:\.\d+)?", expression)
            if not terms or "".join(terms) != expression or any(term[0] not in "+-" for term in terms[1:]):
                return None
            coefficients = [0., 0., 0.]
            for term in terms:
                power = 2 if term.endswith("x^2") else 1 if term.endswith("x") else 0
                value = term[:-3] if power == 2 else term[:-1] if power == 1 else term
                value = value.rstrip("*")
                coefficients[power] += float(value + "1" if value in {"", "+", "-"} else value)
            if template == "linear_function":
                if coefficients[2]:
                    return None
                parameters.update(m=coefficients[1], b=coefficients[0])
            else:
                parameters.update(a=coefficients[2], b=coefficients[1], c=coefficients[0])
        else:
            return None
        description = "Graph of the requested function."
    elif re.search(r"\d", question):
        return None  # An unparsed numeric expression must not become a default curve.
    elif re.search(r"\b(?:sin|cos|sine|cosine)\b", question, re.I) and template == "trigonometric_function":
        parameters["function"] = "cos" if re.search(r"\b(?:cos|cosine)\b", question, re.I) else "sin"
    for key, value in parameters.items():
        spec = TEMPLATES[template]["parameters"][key]
        if "options" not in spec and (not spec["min"] <= value <= spec["max"] or abs(value - round(value, 3)) > 1e-8):
            return None
    if template == "coordinate_points":
        data = [dict(x=parameters["x"], y=parameters["y"])]
    else:
        data = []
        for index in range(21):
            x = -5 + index / 2
            if template == "linear_function":
                y = parameters["m"] * x + parameters["b"]
            elif template == "quadratic_function":
                y = parameters["a"] * x * x + parameters["b"] * x + parameters["c"]
            else:
                function = math.cos if parameters["function"] == "cos" else math.sin
                y = parameters["a"] * function(parameters["k"] * (x - parameters["h"])) + parameters["d"]
            data.append(dict(x=x, y=round(y, 6)))
    return dict(kind="chart", chartType="line", title="Mathematical graph", description=description,
                xKey="x", xLabel="x", yLabel="y", illustrative=not bool(equation),
                series=[dict(key="y", label="y")], data=data)
