#!/usr/bin/env bash
set -euo pipefail

SOURCE=.tsr-v075/run_candidate.sh
TARGET="${RUNNER_TEMP:-/tmp}/run_candidate_v075_final.sh"

python - "$SOURCE" "$TARGET" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
target = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")

text = text.replace(
    "  rm -f .github/workflows/v075-finalize-temp.yml\n",
    "  rm -f .github/workflows/v075-finalize-temp.yml "
    ".github/workflows/v075-verify-temp.yml "
    ".github/workflows/v075-verify-issue-temp.yml\n",
    1,
)

anchor = '''  test "$(git ls-remote origin refs/heads/main | awk '{print $1}')" = "$GITHUB_SHA"
  apply_candidate

  python scripts/sync_runtime_data.py --write
'''
replacement = '''  test "$(git ls-remote origin refs/heads/main | awk '{print $1}')" = "$GITHUB_SHA"
  apply_candidate

  python - <<'CLEANCI'
from pathlib import Path

path = Path(".github/workflows/ci.yml")
text = path.read_text(encoding="utf-8")
text = text.replace("permissions:\\n  contents: write\\n  issues: write\\n", "permissions:\\n  contents: read\\n", 1)
text = text.replace(
    "  compatibility:\\n    if: ${{ !contains(github.event.head_commit.message, '[v075-finalize]') }}\\n",
    "  compatibility:\\n",
    1,
)
text = text.replace(
    "  full-validation:\\n    if: ${{ !contains(github.event.head_commit.message, '[v075-finalize]') }}\\n",
    "  full-validation:\\n",
    1,
)
start = text.find("\\n# BEGIN V075 TEMP FINALIZER\\n")
end = text.find("\\n# END V075 TEMP FINALIZER\\n")
if start < 0 or end < 0 or end <= start:
    raise SystemExit("temporary CI finalizer block missing")
text = text[:start] + text[end + len("\\n# END V075 TEMP FINALIZER\\n"):]
path.write_text(text.rstrip() + "\\n", encoding="utf-8", newline="\\n")
CLEANCI

  python scripts/sync_runtime_data.py --write
'''
if text.count(anchor) != 1:
    raise SystemExit("finalize insertion anchor missing or ambiguous")
text = text.replace(anchor, replacement, 1)

text = text.replace(
    '    ".github/workflows/v075-finalize-temp.yml",\n',
    '    ".github/workflows/v075-finalize-temp.yml",\n'
    '    ".github/workflows/v075-verify-temp.yml",\n'
    '    ".github/workflows/v075-verify-issue-temp.yml",\n',
    1,
)
text = text.replace(
    '    ".tsr-v075/run_candidate.sh",\n',
    '    ".tsr-v075/run_candidate.sh",\n'
    '    ".tsr-v075/run_finalizer.sh",\n',
    1,
)
text = text.replace(
    '    ".github/workflows/v075-finalize-temp.yml",\n    ".tsr-v075/apply.part000",\n',
    '    ".github/workflows/v075-finalize-temp.yml",\n'
    '    ".github/workflows/v075-verify-temp.yml",\n'
    '    ".github/workflows/v075-verify-issue-temp.yml",\n'
    '    ".tsr-v075/apply.part000",\n',
    1,
)
text = text.replace(
    '    ".tsr-v075/run_candidate.sh",\n    "VERSION",\n',
    '    ".tsr-v075/run_candidate.sh",\n'
    '    ".tsr-v075/run_finalizer.sh",\n'
    '    "VERSION",\n',
    1,
)
text = text.replace(
    'for path in (Path(".github/workflows/v075-finalize-temp.yml"), Path(".tsr-v075")):\n',
    'for path in (\n'
    '    Path(".github/workflows/v075-finalize-temp.yml"),\n'
    '    Path(".github/workflows/v075-verify-temp.yml"),\n'
    '    Path(".github/workflows/v075-verify-issue-temp.yml"),\n'
    '    Path(".tsr-v075"),\n'
    '):\n',
    1,
)

target.write_text(text, encoding="utf-8", newline="\n")
PY

chmod +x "$TARGET"
exec bash "$TARGET" finalize
