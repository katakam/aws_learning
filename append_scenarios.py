#!/usr/bin/env python3
"""
append_scenarios.py — Convert raw scenario markdown into exam-container format
and append to README.md.

Usage:
    python append_scenarios.py <source.md> <target.md>

Source format expected (scenarios separated by ---):
    ### Scenario N: Domain X — ...
    <description>
    **Question:** <question text (may wrap lines)>
    - [ ] **A)** option text
    - [ ] **B)** ...
    - [ ] **C)** ...
    - [ ] **D)** ...
    **Architectural Decision Record (Resolution):**
    * **Optimal Solution:** ...
    * **Why it succeeds:** ...
    * **Why alternatives fail:** ...
"""

import re
import sys


HEADER = '<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div>'

TEMPLATE = """\

<div class="exam-container">
{header}

{heading}

{description}

<div class="question-prompt">
{question}
</div>

{options}

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

{adr}

</details>
</div>"""


def parse_scenario(text):
    """Parse a single scenario block into its four sections."""
    lines = text.splitlines()

    # --- locate section boundaries ---
    heading_idx = next(
        (i for i, l in enumerate(lines) if l.startswith("### Scenario")), None
    )
    question_idx = next(
        (i for i, l in enumerate(lines) if l.startswith("**Question:**")), None
    )
    options_idx = next(
        (i for i, l in enumerate(lines) if re.match(r"^- \[ \]", l)), None
    )
    adr_idx = next(
        (i for i, l in enumerate(lines) if l.startswith("**Architectural Decision Record")),
        None,
    )

    if any(idx is None for idx in [heading_idx, question_idx, options_idx, adr_idx]):
        missing = [
            name
            for name, idx in [
                ("heading", heading_idx),
                ("question", question_idx),
                ("options", options_idx),
                ("ADR", adr_idx),
            ]
            if idx is None
        ]
        raise ValueError(f"Could not locate: {', '.join(missing)}")

    heading     = lines[heading_idx].strip()
    description = "\n".join(lines[heading_idx + 1 : question_idx]).strip()
    question    = "\n".join(lines[question_idx : options_idx]).strip()
    options     = "\n".join(lines[options_idx : adr_idx]).strip()
    adr         = "\n".join(lines[adr_idx:]).strip()

    return heading, description, question, options, adr


def format_scenario(text):
    heading, description, question, options, adr = parse_scenario(text)
    return TEMPLATE.format(
        header=HEADER,
        heading=heading,
        description=description,
        question=question,
        options=options,
        adr=adr,
    )


def main():
    if len(sys.argv) != 3:
        print("Usage: python append_scenarios.py <source.md> <target.md>")
        sys.exit(1)

    source_path, target_path = sys.argv[1], sys.argv[2]

    with open(source_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split on --- separators (ignoring blank blocks)
    raw_blocks = re.split(r"\n---\n", content)
    blocks = [b.strip() for b in raw_blocks if b.strip()]

    formatted_blocks = []
    for i, block in enumerate(blocks, 1):
        try:
            formatted_blocks.append(format_scenario(block))
        except ValueError as e:
            print(f"Warning: skipping block {i} — {e}")

    if not formatted_blocks:
        print("No valid scenarios found.")
        sys.exit(1)

    output = "\n".join(formatted_blocks) + "\n"

    with open(target_path, "a", encoding="utf-8") as f:
        f.write(output)

    print(f"Appended {len(formatted_blocks)} scenario(s) to {target_path}")


if __name__ == "__main__":
    main()
