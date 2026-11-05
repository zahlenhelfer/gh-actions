"""Check or fix file endings for the paths listed on stdin, one per line."""

import argparse
import os
import re
import sys

# Wie git: Ein NUL-Byte am Dateianfang bedeutet Binärdatei.
BINARY_SNIFF_BYTES = 8000


def fixed_content(data):
    if not data:
        return data

    stripped = data.rstrip(b"\r\n")
    if not stripped:
        return b""

    ending = data[len(stripped):]
    if ending in (b"\n", b"\r\n"):
        return data

    # Der Zeilenumbruch der Datei bleibt erhalten.
    uses_crlf = ending.startswith(b"\r\n") or (not ending and b"\r\n" in data)
    return stripped + (b"\r\n" if uses_crlf else b"\n")


def escape_data(value):
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def escape_property(value):
    return escape_data(value).replace(":", "%3A").replace(",", "%2C")


def is_checkable(path):
    return path and os.path.isfile(path) and not os.path.islink(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fix", action="store_true", help="repair files instead of failing")
    parser.add_argument("--exclude", help="skip paths matching this regular expression")
    args = parser.parse_args()

    try:
        exclude = re.compile(args.exclude) if args.exclude else None
    except re.error as error:
        print(f"::error title=end-of-file-fixer::Invalid exclude pattern: {escape_data(str(error))}")
        return 1

    checked = 0
    found = 0
    for raw_line in sys.stdin.buffer:
        path = os.fsdecode(raw_line.rstrip(b"\n"))
        if not is_checkable(path) or (exclude and exclude.search(path)):
            continue

        with open(path, "rb") as file:
            data = file.read()
        if b"\0" in data[:BINARY_SNIFF_BYTES]:
            continue
        checked += 1

        fixed = fixed_content(data)
        if fixed == data:
            continue
        found += 1

        location = f"file={escape_property(path)},title=end-of-file-fixer"
        if args.fix:
            with open(path, "wb") as file:
                file.write(fixed)
            print(f"::warning {location}::Fixed: file now ends with exactly one newline")
        else:
            print(f"::error {location}::File must end with exactly one newline")

    action = "fixed" if args.fix else "with a wrong ending"
    print(f"Checked {checked} file(s), {found} {action}")
    return 1 if found and not args.fix else 0


if __name__ == "__main__":
    sys.exit(main())
