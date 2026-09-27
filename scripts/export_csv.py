#!/usr/bin/env python3
"""data/*.json → data/*.csv（UTF-8 BOM，Excel 直接双击不乱码）

用法：python3 scripts/export_csv.py
"""
import csv
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

LAB_COLUMNS = [
    ("university", "学校"),
    ("city", "城市"),
    ("tags", "标签"),
    ("school", "院系"),
    ("group", "课题组"),
    ("pi", "负责人"),
    ("field", "方向类别"),
    ("direction", "研究方向"),
    ("homepage", "主页"),
    ("source", "来源页面"),
    ("note", "备注"),
]
FACULTY_COLUMNS = [("university", "学校"), ("city", "城市"), ("tags", "标签"), ("name", "姓名"), ("homepage", "主页")]


def write(rows, columns, target):
    with target.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([label for _, label in columns])
        for row in rows:
            writer.writerow([
                "、".join(value) if isinstance(value := row.get(key), list) else (value or "")
                for key, _ in columns
            ])
    print(f"{target.name}: {len(rows)} 行")


def main():
    write(json.loads((DATA / "labs.json").read_text(encoding="utf-8")), LAB_COLUMNS, DATA / "labs.csv")
    write(json.loads((DATA / "faculty.json").read_text(encoding="utf-8")), FACULTY_COLUMNS, DATA / "faculty.csv")


if __name__ == "__main__":
    main()
