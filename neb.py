#!/usr/bin/env python3
import os
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

YELLOW = "\033[93m"
GOLD = "\033[33m"
WHITE = "\033[97m"
GRAY = "\033[90m"
RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"
BOLD = "\033[1m"

ENCODE_DIR = Path("/storage/emulated/0/mlbb/encode")
DECODE_DIR = Path("/storage/emulated/0/mlbb/decode")
TARGET_FILE = ENCODE_DIR / "Documents.unity3d"


def clear():
    os.system("clear")


def banner():
    print(f"{YELLOW}{BOLD}")
    print("  ███╗   ██╗███████╗██████╗ ██╗   ██╗██╗      █████╗ ")
    print("  ████╗  ██║██╔════╝██╔══██╗██║   ██║██║     ██╔══██╗")
    print("  ██╔██╗ ██║█████╗  ██████╔╝██║   ██║██║     ███████║")
    print("  ██║╚██╗██║██╔══╝  ██╔══██╗╚██╗ ██╔╝██║     ██╔══██║")
    print("  ██║ ╚████║███████╗██║  ██║ ╚████╔╝ ███████╗██║  ██║")
    print("  ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚═╝  ╚═╝")
    print(f"{RESET}{YELLOW}  🔍 SUPER XYO AUTO MODIFY XML{RESET}")
    print(f"{GOLD}  {'─' * 48}{RESET}")


def pause():
    input(f"\n{YELLOW}Press Enter to back to menu...{RESET}")


def human_size(size):
    units = ("B", "KB", "MB", "GB")
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024


def hex_reader():
    clear()
    banner()
    print(f"{GOLD}FILE HEX READER{RESET}\n")
    print(f"{WHITE}Input: {TARGET_FILE}{RESET}")

    if not TARGET_FILE.is_file():
        print(f"{RED}File not found.{RESET}")
        print(f"{GRAY}Check that Documents.unity3d exists in the encode folder.{RESET}")
        pause()
        return

    try:
        size = TARGET_FILE.stat().st_size
        print(f"{GREEN}File found: {human_size(size)}{RESET}")
        limit_text = input(
            f"{YELLOW}Bytes to display (Enter = first 4096, 0 = all): {RESET}"
        ).strip()
        limit = int(limit_text) if limit_text else 4096
        if limit < 0:
            raise ValueError

        with TARGET_FILE.open("rb") as file:
            data = file.read() if limit == 0 else file.read(limit)

        print(f"\n{GOLD}OFFSET      HEX BYTES                                      ASCII{RESET}")
        for offset in range(0, len(data), 16):
            chunk = data[offset:offset + 16]
            hex_part = " ".join(f"{byte:02X}" for byte in chunk)
            ascii_part = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in chunk)
            print(f"{YELLOW}{offset:08X}  {hex_part:<47}  {ascii_part}{RESET}")

        if limit and size > len(data):
            print(f"\n{GRAY}Showing {len(data)} of {size} bytes.{RESET}")
        print(f"\n{GREEN}Hex read complete. Original file was not modified.{RESET}")
    except ValueError:
        print(f"{RED}Enter a valid non-negative number.{RESET}")
    except OSError as error:
        print(f"{RED}Could not read file: {error}{RESET}")

    pause()


def normalize_code(text):
    return re.sub(r"\s+", "", text).strip()


def valid_xml_files():
    """Return parseable XML files and malformed/unreadable files separately."""
    valid = []
    skipped = []
    if not DECODE_DIR.is_dir():
        return valid, skipped

    for path in sorted(DECODE_DIR.rglob("*")):
        if not path.is_file() or path.suffix.lower() != ".xml":
            continue
        try:
            raw = path.read_bytes()
            ET.fromstring(raw)
            valid.append((path, raw))
        except (ET.ParseError, OSError, UnicodeError, ValueError) as error:
            skipped.append((path, str(error)))
    return valid, skipped


def search_code():
    clear()
    banner()
    print(f"{GOLD}SEARCH CODE IN VALID XML FILES{RESET}\n")
    print(f"{WHITE}Search folder: {DECODE_DIR}{RESET}")
    print("Paste the XML/code snippet to search for.")
    print(f"{GRAY}Malformed XML files are skipped automatically.{RESET}")
    query = input(f"\n{YELLOW}XML code > {RESET}").strip()

    if not query:
        print(f"{RED}No search code entered.{RESET}")
        pause()
        return

    if not DECODE_DIR.is_dir():
        print(f"{RED}Decode folder not found: {DECODE_DIR}{RESET}")
        pause()
        return

    valid, skipped = valid_xml_files()
    if not valid and not skipped:
        print(f"{RED}No XML files found in the decode folder.{RESET}")
        pause()
        return

    query_normal = normalize_code(query)
    matches = []

    print(f"\n{YELLOW}Scanning {len(valid)} valid XML file(s)...{RESET}")
    for path, raw in valid:
        content = raw.decode("utf-8", errors="replace")
        if query_normal in normalize_code(content):
            found_lines = [
                (number, line.strip())
                for number, line in enumerate(content.splitlines(), 1)
                if query_normal in normalize_code(line)
            ]
            matches.append((path, found_lines))

    print(f"\n{GOLD}{'─' * 48}{RESET}")
    if matches:
        print(f"{GREEN}Found matches in {len(matches)} file(s):{RESET}\n")
        for path, found_lines in matches:
            print(f"{YELLOW}FILE: {path}{RESET}")
            if found_lines:
                for number, line in found_lines[:20]:
                    preview = line if len(line) <= 220 else line[:217] + "..."
                    print(f"{WHITE}  Line {number}: {preview}{RESET}")
                if len(found_lines) > 20:
                    print(f"{GRAY}  ... and {len(found_lines) - 20} more matching line(s){RESET}")
            else:
                print(f"{GRAY}  Code matched across whitespace or line boundaries.{RESET}")
            print()
    else:
        print(f"{RED}No matching code found in valid XML files.{RESET}")

    print(f"{GRAY}Malformed/unreadable XML files skipped: {len(skipped)}{RESET}")
    print(f"{GREEN}Search complete. No files were modified.{RESET}")
    pause()


def modify_code():
    clear()
    banner()
    print(f"{GOLD}MODIFY CODE IN VALID XML FILES{RESET}\n")
    print(f"{WHITE}Folder: {DECODE_DIR}{RESET}")
    print(f"{GRAY}Only well-formed XML files are considered. Files are changed only after confirmation.{RESET}\n")

    old_code = input(f"{YELLOW}Existing XML code/value > {RESET}").strip()
    if not old_code:
        print(f"{RED}Existing code cannot be empty.{RESET}")
        pause()
        return

    new_code = input(f"{YELLOW}Replacement code/value > {RESET}")
    old_normal = normalize_code(old_code)
    valid, skipped = valid_xml_files()
    found = []

    for path, raw in valid:
        content = raw.decode("utf-8", errors="replace")
        # Replace exact text while allowing whitespace differences in the search.
        if old_code in content:
            found.append((path, content, content.count(old_code)))

    if not found:
        print(f"\n{RED}No exact text matches found in valid XML files.{RESET}")
        print(f"{GRAY}Tip: enter the exact snippet as it appears in the file, including spacing.{RESET}")
        print(f"{GRAY}Malformed/unreadable XML files skipped: {len(skipped)}{RESET}")
        pause()
        return

    total = sum(count for _, _, count in found)
    print(f"\n{GREEN}Found {total} exact occurrence(s) across {len(found)} file(s):{RESET}")
    for path, _, count in found:
        print(f"{YELLOW}{path}{WHITE} — {count} occurrence(s){RESET}")

    confirm = input(f"\n{RED}Replace these occurrences and save the files? Type YES to confirm: {RESET}").strip()
    if confirm.lower() != "yes":
        print(f"{GRAY}Cancelled. No files changed.{RESET}")
        pause()
        return

    changed_files = 0
    changed_occurrences = 0
    failures = []

    for path, content, count in found:
        updated = content.replace(old_code, new_code)
        try:
            # Validate the replacement before writing anything.
            ET.fromstring(updated)
            # Atomic write in the same directory, preserving the original on write failure.
            fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="") as temp_file:
                    temp_file.write(updated)
                    temp_file.flush()
                    os.fsync(temp_file.fileno())
                os.replace(temp_name, path)
            except Exception:
                try:
                    os.unlink(temp_name)
                except OSError:
                    pass
                raise
            changed_files += 1
            changed_occurrences += count
            print(f"{GREEN}Updated: {path}{RESET}")
        except (ET.ParseError, OSError, UnicodeError, ValueError) as error:
            failures.append((path, str(error)))
            print(f"{RED}Skipped {path}: replacement would be invalid XML or file write failed ({error}){RESET}")

    print(f"\n{GREEN}Done: {changed_occurrences} occurrence(s) changed in {changed_files} file(s).{RESET}")
    print(f"{GRAY}Malformed/unreadable XML files skipped during scan: {len(skipped)}{RESET}")
    if failures:
        print(f"{RED}Files not updated: {len(failures)}{RESET}")
    pause()


def main():
    while True:
        clear()
        banner()
        print(f"{YELLOW}  [1]{WHITE} File hex reader")
        print(f"{YELLOW}  [2]{WHITE} Search Code")
        print(f"{YELLOW}  [3]{WHITE} Modify XML Code")
        print(f"{YELLOW}  [0]{WHITE} Exit")
        print(f"{GOLD}  {'─' * 48}{RESET}")
        choice = input(f"{YELLOW}  Select option > {RESET}").strip()

        if choice == "1":
            hex_reader()
        elif choice == "2":
            search_code()
        elif choice == "3":
            modify_code()
        elif choice == "0":
            clear()
            print(f"{YELLOW}NEBULA{RESET} {GRAY}Exiting...{RESET}")
            break
        else:
            print(f"{RED}Invalid option.{RESET}")
            input(f"{YELLOW}Press Enter to continue...{RESET}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Exiting NEBULA.{RESET}")
        sys.exit(0)
