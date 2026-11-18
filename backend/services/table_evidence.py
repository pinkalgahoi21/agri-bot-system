import re


FORMULATION = re.compile(r"\b\d+(?:\.\d+)?\s*%\s*(?:W\.?P|S\.?C|W\.?G|E\.?C|L\.?F|A\.?S|W\.?D\.?G|S\.?L)\b", re.I)


def linked_entry(page, crop, issue):
    lines = [" ".join(line.split()) for line in page.splitlines() if line.strip()]
    heading = None
    for pos, line in enumerate(lines):
        if FORMULATION.search(line):
            heading = line if re.match(r"^[A-Za-z]", line) and not re.search(r"\b(spray|apply|mix|treatment|water)\b", line, re.I) else None
            continue
        if not heading or not re.match(re.escape(crop) + r"\b", line, re.I):
            continue
        if re.search(r"\b" + re.escape(issue) + r"\b", line, re.I):
            return heading, line
        if pos and lines[pos - 1].lower().startswith(issue.lower() + " (caused") and "by " in line.lower():
            return heading, lines[pos - 1] + "\n" + line
    return None
