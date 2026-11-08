# Drafting playbook

Ross's drafting experience, written as rules the auto-draft agent is checked against.
Started 08/11/2026. Draft structure: Ross fills it in, the reviewer checks it.

## How it works
1. Every mistake Ross catches (or a client marks) becomes a rule in `playbook.md`.
2. Every rule says how it is checked: automatically (a script), visually (render and look), or by Ross.
3. Every rule links to the job it came from, so we can re-run that job as a test.
4. The agent cannot hand back a drawing until every rule that applies to it has passed.

## Files
- `playbook.md`: the rules, grouped by topic. Start here.
- `rule-template.md`: copy this to add a rule.
- `test-case-template.md`: copy this for each job in the test set (Ross's issued drawing, the client markup, what he changed).

## Rule status
- `draft`: written down, not checked by anything yet
- `manual`: Ross or a person checks it
- `auto`: a script checks it (name the script)
- `retired`: no longer applies (keep it, say why)

## Adding a rule (2 minutes)
Copy `rule-template.md`, fill the six fields, give it the next ID (R-009, R-010...), add it under the right heading in `playbook.md`.
Short and plain. One rule, one idea. A fail example is more useful than a long explanation.

## Order of work
1. Ross picks 5 drawings for the test set (use the test-case template).
2. Ross reads the seeded rules in `playbook.md` and corrects them.
3. Reviewer turns each rule's check into a script or a render check, one at a time.
4. Run the agent on the 5 drawings. Every miss becomes a new rule.
5. Repeat with 5 more. Track: first-pass acceptance, defects Ross finds (target: zero).

## Privacy
Do not put client names, drawings or markups in this folder. Use job numbers and describe the change. The drawings stay on the NAS (dc-private).
