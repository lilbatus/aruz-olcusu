import json
from html import escape
from importlib.resources import files

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from aruz import strings
from aruz.poem import scan
from aruz.repair import restore
from aruz.report import poem_dict, repair_dict

PAGE_KEYS = [
    "WEB_TITLE", "WEB_HEADING", "WEB_INTRO", "WEB_PLACEHOLDER", "WEB_BUTTON", "WEB_ERROR", "WEB_REPAIR",
    "METER", "CONFIDENCE", "PENALTY", "ALTERNATIVES", "BAD_FIT", "NO_FIT", "NO_LICENSE", "BEYIT", "SYLLABLE",
    "REPAIR_LABEL", "PERCENT", "DECIMAL", "LANG_LABEL", "LANG_TR", "LANG_EN", "SCAN_TIP", "REPAIR_TIP",
]

app = FastAPI()


class ScanRequest(BaseModel):
    text: str
    repair: bool = False
    choices: dict[int, int] = {}


def page_strings() -> str:
    data = {lang: {key: words[key] for key in PAGE_KEYS} for lang, words in strings.LANGUAGES.items()}
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def page() -> str:
    html = files("aruz").joinpath("web/index.html").read_text("utf-8").replace("__STRINGS__", page_strings())
    for key in PAGE_KEYS:
        html = html.replace(f"__{key}__", escape(strings.LANGUAGES[strings.DEFAULT][key]))
    return html


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return page()


@app.post("/api/scan")
def scan_text(request: ScanRequest) -> dict:
    if not request.text.strip():
        raise HTTPException(status_code=400, detail=strings.LANGUAGES[strings.DEFAULT]["EMPTY"])
    if not request.repair:
        return poem_dict(scan(request.text))
    restoration = restore(request.text, choices=request.choices)
    report = poem_dict(scan(restoration.text))
    report["repair"] = repair_dict(restoration)
    return report


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
