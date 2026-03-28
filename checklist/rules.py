"""Rule evaluator for CheckItem.auto_check_rule JSON conditions."""


def collect_datarefs(rule: dict) -> list:
    """
    Return all dataref paths referenced in a rule dict.
    May contain duplicates — callers should deduplicate as needed.
    """
    if "all" in rule:
        result = []
        for r in rule["all"]:
            result.extend(collect_datarefs(r))
        return result
    if "any" in rule:
        result = []
        for r in rule["any"]:
            result.extend(collect_datarefs(r))
        return result
    dr = rule.get("dataref")
    return [dr] if dr else []


_OPS = {
    "eq":  lambda a, v: a == v,
    "neq": lambda a, v: a != v,
    "gt":  lambda a, v: a >  v,
    "gte": lambda a, v: a >= v,
    "lt":  lambda a, v: a <  v,
    "lte": lambda a, v: a <= v,
}


def evaluate_rule(rule: dict, state: dict) -> bool:
    """
    Evaluate an auto_check_rule JSON dict against a dataref state dict.

    rule  — parsed CheckItem.auto_check_rule value
    state — {dataref_path: value} received from the plugin

    Returns True when the condition is satisfied.
    """
    if "all" in rule:
        return all(evaluate_rule(r, state) for r in rule["all"])

    if "any" in rule:
        return any(evaluate_rule(r, state) for r in rule["any"])

    dataref = rule.get("dataref")
    op      = rule.get("op")
    value   = rule.get("value")

    if dataref not in state:
        return False

    fn = _OPS.get(op)
    if fn is None:
        return False

    return fn(state[dataref], value)
