from aruz import strings


def leaves(table: dict, path: tuple = ()):
    for key, value in table.items():
        if isinstance(value, dict):
            yield from leaves(value, path + (key,))
        else:
            yield ".".join(path + (key,)), value


def cell(text: str) -> str:
    return text.replace("\n", " / ").replace("|", "\\|")


def main() -> None:
    english = dict(leaves(strings.EN))
    print("| key | TR | EN |")
    print("| --- | --- | --- |")
    for key, value in leaves(strings.TR):
        print(f"| `{key}` | {cell(value)} | {cell(english[key])} |")


if __name__ == "__main__":
    main()
