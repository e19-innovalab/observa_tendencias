"""Load ESCO skill definitions and hierarchy groups for the skills already stored.

    python -m app.jobs.esco_hierarchy

Also runs after every ESCO update (app/skills/esco.py). Then recompute the skill gaps
(python -m app.jobs.recompute) to get the gaps per group.
"""
from app.core.database import SessionLocal
from app.skills.esco_hierarchy import run_esco_hierarchy

SOURCE = "esco"


def main() -> None:
    with SessionLocal() as session:
        skills, groups, failed = run_esco_hierarchy(session, SOURCE)
        session.commit()
    print(f"skills with a group: {skills} | hierarchy concepts: {groups}"
          + (f" | skipped (ESCO server error): {', '.join(failed)}" if failed else ""))


if __name__ == "__main__":
    main()
