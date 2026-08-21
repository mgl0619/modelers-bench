"""Report lessons whose `reviewed:` date is more than 18 months old."""

import datetime as dt
import pathlib
import sys

import yaml

MAX_AGE_DAYS = 548          # 18 months
today = dt.date.today()
stale = []

for meta_path in sorted(pathlib.Path("lessons").glob("*/meta.yml")):
    meta = yaml.safe_load(meta_path.read_text())
    reviewed = meta.get("reviewed")
    if reviewed is None:
        stale.append((meta_path.parent.name, "no reviewed date", None))
        continue
    if isinstance(reviewed, str):
        reviewed = dt.date.fromisoformat(reviewed)
    age = (today - reviewed).days
    if age > MAX_AGE_DAYS:
        stale.append((meta_path.parent.name, meta.get("title", ""), age))

if not stale:
    print(f"All lessons reviewed within {MAX_AGE_DAYS} days.")
    sys.exit(0)

print(f"{len(stale)} lesson(s) need review:\n")
for slug, title, age in stale:
    age_str = f"{age} days old" if age else title
    print(f"  {slug:40s} {age_str}")

# In CI, turn this into an issue rather than a failure.
print("\n::warning::Stale lessons found — open a review issue.")
