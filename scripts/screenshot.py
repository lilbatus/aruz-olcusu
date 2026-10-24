import io
import re
from pathlib import Path

from rich.console import Console
from rich.terminal_theme import TerminalTheme

from aruz.cli import render
from aruz.poem import scan
from aruz.report import poem_dict

BEYIT = "Beni candan usandırdı cefâdan yâr usanmaz mı\nFelekler yandı âhımdan murâdım şem'i yanmaz mı"
OUT = Path(__file__).resolve().parent.parent / "docs" / "scan.svg"

BLACK = TerminalTheme(
    (0, 0, 0),
    (212, 212, 212),
    [(0, 0, 0), (205, 49, 49), (13, 188, 121), (229, 229, 16), (36, 114, 200), (188, 63, 188), (17, 168, 205), (229, 229, 229)],
    [(102, 102, 102), (241, 76, 76), (35, 209, 139), (245, 245, 67), (59, 142, 234), (214, 112, 214), (41, 184, 219), (255, 255, 255)],
)


def main() -> None:
    console = Console(record=True, width=84, file=io.StringIO(), highlight=False)
    render(poem_dict(scan(BEYIT)), console)
    OUT.parent.mkdir(exist_ok=True)
    svg = console.export_svg(title="aruz", theme=BLACK)
    OUT.write_text(re.sub(r"<circle[^>]*/>", "", svg), "utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
