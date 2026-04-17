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


def _resolve_ref(rule: dict, state: dict):
    """
    Resolve the comparison base value for a leaf rule.
    Returns (value, missing: bool).

    - "ref" rules: looks up state[ref], applies optional ref_index then delta.
    - Plain "value" rules: returns rule["value"].

    ref_index: int — extract element N from an array-valued dataref.
    delta: number  — added to the resolved value (ignored for abs_diff_lte).
    """
    if "ref" in rule:
        ref_path = rule["ref"]
        if ref_path not in state:
            return None, True
        ref_val = state[ref_path]
        if "ref_index" in rule:
            try:
                ref_val = ref_val[rule["ref_index"]]
            except (IndexError, TypeError):
                return None, True
        try:
            return ref_val + rule.get("delta", 0), False
        except TypeError:
            return ref_val, False
    return rule.get("value"), False


def collect_leaf_evaluations(rule: dict, state: dict) -> list:
    """
    Flatten a rule into individual leaf-condition results for debug display.
    Each result dict: {"dataref", "op", "required", "actual", "pass"}
    Handles nested all/any, fmc_line, ref/ref_index comparisons, abs_diff_lte.
    """
    if "all" in rule:
        out = []
        for r in rule["all"]:
            out.extend(collect_leaf_evaluations(r, state))
        return out
    if "any" in rule:
        out = []
        for r in rule["any"]:
            out.extend(collect_leaf_evaluations(r, state))
        return out
    if "fmc_line" in rule:
        path = rule["fmc_line"]
        actual = state.get(path, "<missing>")
        if "contains" in rule:
            op, required = "contains", rule["contains"]
            passed = required in str(actual) if actual != "<missing>" else False
        else:
            op, required = "not_contains", rule.get("not_contains", "")
            passed = required not in str(actual) if actual != "<missing>" else False
        return [{"dataref": path, "op": op, "required": required, "actual": actual, "pass": passed}]

    dataref = rule.get("dataref")
    op      = rule.get("op", "?")
    actual  = state.get(dataref, "<missing>")

    compare_val, missing = _resolve_ref(rule, state)

    if "ref" in rule:
        ref_path = rule["ref"]
        idx      = rule.get("ref_index")
        delta    = rule.get("delta", 0)
        if idx is not None:
            label = f"{ref_path}[{idx}]"
        elif delta:
            label = f"{ref_path}+{delta}"
        else:
            label = ref_path
        if op == "abs_diff_lte":
            tolerance = rule.get("tolerance", 0)
            required  = f"{label} ±{tolerance}"
        else:
            required = label
    else:
        required = rule.get("value")

    if missing:
        passed = False
    elif op == "abs_diff_lte":
        tolerance = rule.get("tolerance", 0)
        try:
            passed = abs(actual - compare_val) <= tolerance
        except TypeError:
            passed = False
    else:
        fn = _OPS.get(op)
        try:
            passed = fn is not None and actual != "<missing>" and fn(actual, compare_val)
        except TypeError:
            passed = False

    return [{"dataref": dataref, "op": op, "required": required, "actual": actual, "pass": passed}]


def evaluate_rule(rule: dict, state: dict) -> bool:
    """
    Evaluate an auto_check_rule JSON dict against a dataref state dict.

    rule  — parsed CheckItem.auto_check_rule value
    state — {dataref_path: value} received from the plugin

    Returns True when the condition is satisfied.

    Supported leaf shapes:
      {"dataref", "op", "value"}                      — compare against constant
      {"dataref", "op", "ref"}                         — compare against live dataref
      {"dataref", "op", "ref", "ref_index"}            — compare against array element
      {"dataref", "op", "ref", "ref_index", "delta"}   — …with offset
      {"dataref", "abs_diff_lte", "ref", "ref_index",
       "tolerance"}                                    — |a − b| ≤ tolerance
      {"fmc_line", "contains"/"not_contains", …}       — CDU screen-buffer check
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

    compare_val, missing = _resolve_ref(rule, state)
    if missing:
        return False

    # abs_diff_lte: |dataref − ref[index]| ≤ tolerance
    if op == "abs_diff_lte":
        tolerance = rule.get("tolerance", 0)
        try:
            return abs(state[dataref] - compare_val) <= tolerance
        except TypeError:
            return False

    fn = _OPS.get(op)
    return fn is not None and fn(state[dataref], compare_val)
