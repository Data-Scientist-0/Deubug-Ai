import re


def extract_fixed_code(response_text: str) -> str:
    """Pull out the first python code block from the response."""
    matches = re.findall(r"```python\n(.*?)```", response_text, re.DOTALL)
    if matches:
        return matches[0].strip()
    # fallback: any code block
    matches = re.findall(r"```\n(.*?)```", response_text, re.DOTALL)
    if matches:
        return matches[0].strip()
    return ""


def extract_bug_count(response_text: str) -> int:
    """Extract total bug count from the header line."""
    match = re.search(r"Bugs Found\s*\((\d+)\s*total\)", response_text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 0


def extract_stack(response_text: str) -> str:
    """Extract the detected stack line."""
    match = re.search(r"## Stack Detected\n(.+?)(?:\n|$)", response_text)
    if match:
        return match.group(1).strip()
    return "Not detected"


def extract_severity_counts(response_text: str) -> dict:
    """Count severities mentioned in the bug table."""
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for key in counts:
        counts[key] = len(re.findall(key, response_text, re.IGNORECASE))
    return counts


def parse_response(response_text: str) -> dict:
    """Return a structured dict from the raw LLM response."""
    return {
        "raw": response_text,
        "fixed_code": extract_fixed_code(response_text),
        "bug_count": extract_bug_count(response_text),
        "stack": extract_stack(response_text),
        "severity_counts": extract_severity_counts(response_text),
    }