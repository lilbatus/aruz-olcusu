import argparse
import json
import sys
from pathlib import Path

from rich.console import Console, Group
from rich.padding import Padding
from rich.table import Table
from rich.text import Text

from aruz import strings
from aruz.poem import scan
from aruz.repair import restore
from aruz.report import number, poem_dict, repair_dict

ACCENT = "#d4a35a"
TEXT = "#d4d4d4"
DIM = "#6e6e6e"
WORDS = strings.TR


def foot_cell(foot: dict) -> Text:
    top = Text()
    bottom = Text()
    for unit in foot["units"]:
        width = max(len(unit["text"]), 1)
        style = ACCENT if unit["license"] else TEXT
        top.append(unit["text"].ljust(width) + " ", style)
        bottom.append(unit["mark"].ljust(width) + " ", ACCENT if unit["license"] else DIM)
    return Text("\n").join([top, bottom])


def license_line(licenses: list[dict]) -> Text:
    if not licenses:
        return Text(WORDS["NO_LICENSE"], DIM)
    line = Text()
    for i, lic in enumerate(licenses):
        if i:
            line.append("   ")
        line.append(lic["name"] + " ", DIM)
        line.append(lic["text"], ACCENT)
        line.append(" " + WORDS["SYLLABLE"].format(n=lic["syllable"]), DIM)
    return line


def reasons_table(fit: dict) -> Table:
    grid = Table(box=None, show_edge=False, show_header=False, padding=(0, 2, 0, 0))
    grid.add_column(style=DIM, justify="right", no_wrap=True)
    grid.add_column(style=TEXT, no_wrap=True)
    grid.add_column(style=DIM, no_wrap=True)
    grid.add_column(style=ACCENT, no_wrap=True)
    grid.add_column(style=DIM, overflow="fold", ratio=1)
    for syllable in fit["syllables"]:
        for i, reason in enumerate(syllable["reasons"]):
            head = (str(syllable["position"]), syllable["text"], " ".join(syllable["mark"])) if i == 0 else ("", "", "")
            grid.add_row(*head, reason["name"], reason["text"])
    return grid


def misra_block(misra: dict, explain: bool = False) -> Group:
    fit = misra["fit"]
    if fit is None:
        return Group(Text(misra["text"], TEXT), Text(WORDS["NO_FIT"], ACCENT), Text())
    grid = Table(box=None, show_edge=False, padding=(0, 2, 0, 0), header_style=DIM)
    for foot in fit["feet"]:
        grid.add_column(foot["name"], no_wrap=True)
    grid.add_row(*[foot_cell(foot) for foot in fit["feet"]])
    parts = [Text(misra["text"], DIM), grid, license_line(fit["licenses"])]
    if explain:
        parts += [Text(), reasons_table(fit)]
    return Group(*parts, Text())


def restored_block(repair: dict) -> Group:
    found = {word["index"]: word for word in repair["words"]}
    line = Text()
    for segment in repair["segments"]:
        word = found.get(segment["word"])
        if word is None:
            line.append(segment["text"], TEXT)
            continue
        marks = set(word["changed"])
        extra = " underline" if word["uncertain"] else ""
        for i, ch in enumerate(word["restored"]):
            line.append(ch, (ACCENT if i in marks else TEXT) + extra)
    return Group(Text(WORDS["REPAIR_LABEL"], DIM), line, Text())


def header(report: dict) -> Group:
    meter = report["meter"]
    title = Text()
    title.append(WORDS["METER"] + "  ", DIM)
    title.append(meter["feet"], f"bold {ACCENT}")
    stats = Text()
    stats.append(f"{WORDS['CONFIDENCE']} ", DIM)
    stats.append(WORDS["PERCENT"].format(value=number(report["confidence"] * 100, digits=1)), TEXT)
    stats.append(f"   {WORDS['PENALTY']} ", DIM)
    stats.append(number(meter["penalty"]), TEXT)
    return Group(title, Text(" " * (len(WORDS["METER"]) + 2) + meter["name"], DIM), stats, Text())


def alternatives(report: dict) -> Group:
    grid = Table(box=None, show_edge=False, show_header=False, padding=(0, 3, 0, 2))
    grid.add_column(style=TEXT, no_wrap=True)
    grid.add_column(style=DIM, no_wrap=True)
    for alt in report["alternatives"]:
        grid.add_row(alt["feet"], f"{WORDS['PENALTY']} {number(alt['penalty'])}")
    return Group(Text(WORDS["ALTERNATIVES"], DIM), grid)


def render(report: dict, console: Console, explain: bool = False) -> None:
    console.print()
    if "repair" in report:
        console.print(Padding(restored_block(report["repair"]), (0, 2)))
    console.print(Padding(header(report), (0, 2)))
    many = len(report["beyits"]) > 1
    for beyit in report["beyits"]:
        blocks = []
        if many or beyit["flagged"]:
            label = Text(WORDS["BEYIT"].format(n=beyit["index"]), DIM)
            if beyit["flagged"]:
                label.append("   " + WORDS["BAD_FIT"], ACCENT)
            blocks.append(label)
        blocks.extend(misra_block(m, explain) for m in beyit["misras"])
        console.print(Padding(Group(*blocks), (0, 2)))
    console.print(Padding(alternatives(report), (0, 2)))
    console.print()


def read_input(args: argparse.Namespace) -> str:
    if args.file:
        path = Path(args.file)
        if not path.is_file():
            raise SystemExit(WORDS["FILE_MISSING"].format(path=path))
        return path.read_text("utf-8")
    if args.text:
        return " ".join(args.text)
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(prog="aruz", description=WORDS["CLI_DESCRIPTION"])
    parser.add_argument("text", nargs="*", help=WORDS["CLI_TEXT"])
    parser.add_argument("--file", "-f", help=WORDS["CLI_FILE"])
    parser.add_argument("--json", action="store_true", help=WORDS["CLI_JSON"])
    parser.add_argument("--explain", action="store_true", help=WORDS["CLI_EXPLAIN"])
    parser.add_argument("--repair", action="store_true", help=WORDS["CLI_REPAIR"])
    args = parser.parse_args()
    text = read_input(args)
    if not text.strip():
        raise SystemExit(WORDS["EMPTY"])
    if args.repair:
        restoration = restore(text)
        report = poem_dict(scan(restoration.text))
        report["repair"] = repair_dict(restoration)
    else:
        report = poem_dict(scan(text))
    if args.json:
        sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    render(report, Console(highlight=False), args.explain)


if __name__ == "__main__":
    main()
