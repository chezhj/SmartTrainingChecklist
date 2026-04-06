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
    if "fmc_line" in rule:
        return [rule["fmc_line"]]
    result = []
    if dr := rule.get("dataref"):
        result.append(dr)
    if ref := rule.get("ref"):          # live-dataref comparison value
        result.append(ref)
    return result


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

    # fmc_line: check CDU screen-buffer string datarefs.
    # Rule shape: {"fmc_line": "<dataref>", "contains": "<substr>"}
    #          or {"fmc_line": "<dataref>", "not_contains": "<substr>"}
    # Optional "tail": N  — check only last N chars of the line.
    # Optional "head": N  — check only first N chars of the line.
    # Optional "count_gte": N  — require contains substring ≥ N times.
    if "fmc_line" in rule:
        path = rule["fmc_line"]
        if path not in state:
            return False
        text = str(state[path])
        if "tail" in rule:
            text = text[-rule["tail"]:]
        elif "head" in rule:
            text = text[:rule["head"]]
        if "not_contains" in rule:
            return rule["not_contains"] not in text
        substr = rule.get("contains", "")
        if "count_gte" in rule:
            return text.count(substr) >= rule["count_gte"]
        return substr in text

    dataref = rule.get("dataref")
    op      = rule.get("op")

    if dataref not in state:
        return False

    # "ref" allows comparing against a live dataref value instead of a constant.
    # An optional "delta" is added to the ref value before comparison.
    if "ref" in rule:
        ref = rule["ref"]
        if ref not in state:
            return False
        value = state[ref] + rule.get("delta", 0)
    else:
        value = rule.get("value")

    fn = _OPS.get(op)
    return fn is not None and fn(state[dataref], value)
