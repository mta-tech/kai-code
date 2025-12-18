from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Skill:
    skill_id: str
    path: Path


def discover_skills(root_dir: Path, skills_dir: str = ".skills") -> list[Skill]:
    base = (root_dir / skills_dir).resolve()
    if not base.exists() or not base.is_dir():
        return []
    skills: list[Skill] = []
    for path in base.rglob("SKILL.MD"):
        try:
            rel = path.relative_to(base)
        except ValueError:
            continue
        # skill id = directory path without trailing SKILL.MD
        skill_id = str(rel.parent).replace("\\", "/")
        skills.append(Skill(skill_id=skill_id, path=path))
    skills.sort(key=lambda s: s.skill_id)
    return skills


def format_skills_for_prompt(skills: list[Skill], *, skills_dir: str = ".skills") -> str:
    if not skills:
        return ""
    lines = [
        "Project skills were discovered in ./.skills (read with glob/read_file):",
    ]
    for s in skills:
        # agent will use virtual paths, but we only have real path here; prompt should be generic
        lines.append(f"- {s.skill_id}: {skills_dir}/{s.skill_id}/SKILL.MD")
    return "\n".join(lines)


