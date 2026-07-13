"""Load exam content (task statements + verification checks) from XML.

One file per project in ``content/tasks/projet{n}.xml``. Shared by the UI
(which needs the statements) and the grading engine (which needs the checks).

XML shape::

    <project id="6" workbook="MOS_Excel2016_Projet6.xlsx" title="Les Forums">
      <task id="1" points="1">
        <statement><![CDATA[ ... ]]></statement>
        <check type="formula" sheet="Les Forums" cell="K10" pattern="..."/>
      </task>
      <task id="4">
        <statement><![CDATA[ ... ]]></statement>
        <check type="table_absent" sheet="Les Forums"/>
        <any>                          <!-- passes if ANY child check passes -->
          <check type="formula" cell="C8" pattern="CONCATENER"/>
          <check type="formula" cell="C8" pattern="&amp;"/>
        </any>
      </task>
    </project>

A task passes iff every top-level requirement passes. A bare ``<check>`` is a
requirement on its own; an ``<any>`` requirement passes iff at least one of its
child checks passes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from lxml import etree

from . import config


@dataclass(frozen=True)
class Check:
    type: str
    params: dict[str, str]


@dataclass(frozen=True)
class AnyGroup:
    checks: tuple[Check, ...]


@dataclass
class Task:
    id: int
    points: int
    statement: str
    requirements: list = field(default_factory=list)  # Check | AnyGroup


@dataclass
class Project:
    id: int
    workbook: str
    title: str
    tasks: list[Task]

    @property
    def total_points(self) -> int:
        return sum(t.points for t in self.tasks)


def _parse_check(el: etree._Element) -> Check:
    params = {k: v for k, v in el.attrib.items() if k != "type"}
    return Check(type=el.attrib["type"], params=params)


def load_project(project_no: int) -> Project:
    path = config.task_file(project_no)
    if not path.exists():
        raise FileNotFoundError(f"Task file missing: {path}")
    root = etree.parse(str(path)).getroot()

    tasks: list[Task] = []
    for tel in root.findall("task"):
        statement_el = tel.find("statement")
        statement = (statement_el.text or "").strip() if statement_el is not None else ""
        task = Task(
            id=int(tel.attrib["id"]),
            points=int(tel.attrib.get("points", "1")),
            statement=statement,
        )
        for child in tel:
            if child.tag == "check":
                task.requirements.append(_parse_check(child))
            elif child.tag == "any":
                task.requirements.append(
                    AnyGroup(tuple(_parse_check(c) for c in child.findall("check")))
                )
        tasks.append(task)

    return Project(
        id=int(root.attrib["id"]),
        workbook=root.attrib["workbook"],
        title=root.attrib.get("title", f"Projet {project_no}"),
        tasks=tasks,
    )


@lru_cache(maxsize=None)
def load_project_cached(project_no: int) -> Project:
    return load_project(project_no)


def available_projects() -> list[int]:
    """Project numbers that currently have a task file on disk."""
    found = []
    for n in range(1, 14):
        if config.task_file(n).exists():
            found.append(n)
    return found
