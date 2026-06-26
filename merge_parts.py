#!/usr/bin/env python3
"""
bytejoin-cli

Drop this script into a folder with split files and run it. The default flow
auto-detects the obvious parts, shows the merge order, asks for one Enter press,
then writes the merged output with a live progress display.

This tool only joins bytes in order. Use it only with files you are allowed
to process.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


VERSION = "1.0"
CHUNK_SIZE = 16 * 1024 * 1024
SCREEN_WIDTH = 57
PROJECT_ROOT = Path(__file__).resolve().parent
REAL_FOLDER_NAME = "parts"
DEMO_FOLDER_NAME = "demo_parts"
SCRIPT_NAMES = {Path(__file__).name.lower()}
IGNORED_NAMES = {
    ".gitignore",
    "gitignore",
    "license",
    "readme.md",
    "run_test.txt",
}


@dataclass
class Candidate:
    label: str
    files: list[Path]
    output_name: str
    source: str
    priority: int


@dataclass
class NumberInfo:
    path: Path
    number: int


class Theme:
    def __init__(self, enabled: bool):
        self.enabled = enabled

    def paint(self, text: str, code: str) -> str:
        if not self.enabled:
            return text
        return f"\033[{code}m{text}\033[0m"

    def cyan(self, text: str) -> str:
        return self.paint(text, "36")

    def green(self, text: str) -> str:
        return self.paint(text, "32")

    def yellow(self, text: str) -> str:
        return self.paint(text, "33")

    def red(self, text: str) -> str:
        return self.paint(text, "31")

    def bold(self, text: str) -> str:
        return self.paint(text, "1")


def unicode_symbols() -> dict[str, str]:
    encoding = (sys.stdout.encoding or "").lower()
    if "utf" in encoding:
        return {
            "check": "\u2713",
            "bar": "\u2588",
            "empty": "-",
        }
    return {"check": "OK", "bar": "#", "empty": "-"}


SYMBOLS = unicode_symbols()


def enable_windows_ansi() -> None:
    if os.name == "nt":
        os.system("")


def separator() -> str:
    return "=" * SCREEN_WIDTH


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(PROJECT_ROOT))
    except ValueError:
        try:
            return str(resolved.relative_to(Path.cwd().resolve()))
        except ValueError:
            return str(resolved)


def friendly_folder_name(path: Path) -> str:
    resolved = path.resolve()
    if resolved == PROJECT_ROOT:
        return "project folder"
    if resolved == Path.cwd().resolve():
        return "this folder"
    return display_path(resolved)


def print_header(theme: Theme) -> None:
    print(separator())
    print(theme.bold(f"{'bytejoin-cli v' + VERSION:^57}"))
    print(separator())
    print()


def ensure_standard_folders() -> None:
    (PROJECT_ROOT / REAL_FOLDER_NAME).mkdir(exist_ok=True)
    (PROJECT_ROOT / DEMO_FOLDER_NAME).mkdir(exist_ok=True)


def natural_sort_key(path: Path) -> list[object]:
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r"(\d+)", path.name)
    ]


def numbered_suffix_key(path: Path) -> tuple[int, list[object]]:
    match = re.search(r"\.(\d{2,})$", path.name)
    if match:
        return int(match.group(1)), natural_sort_key(path)
    return 0, natural_sort_key(path)


def extract_part_number(path: Path) -> Optional[int]:
    patterns = [
        r"\.(\d{2,})$",
        r"[._-](\d+)(?:\.[^.]+)$",
        r"(?:part|pt)[._ -]?(\d+)(?:\.[^.]+)?$",
    ]
    for pattern in patterns:
        match = re.search(pattern, path.name, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def format_size(size_bytes: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(size_bytes)

    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{size:.0f} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024

    return f"{size_bytes:.0f} B"


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def human_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    return f"{minutes}m {secs}s"


def progress_bar(done: int, total: int, width: int = 31) -> str:
    if total <= 0:
        return SYMBOLS["empty"] * width + " 0.0 %"
    ratio = min(max(done / total, 0), 1)
    filled = int(width * ratio)
    return (
        SYMBOLS["bar"] * filled
        + SYMBOLS["empty"] * (width - filled)
        + f" {ratio * 100:5.1f} %"
    )


def calculate_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as file:
        while True:
            chunk = file.read(CHUNK_SIZE)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def is_candidate_file(path: Path) -> bool:
    name = path.name.lower()
    if not path.is_file():
        return False
    if name in SCRIPT_NAMES or name in IGNORED_NAMES:
        return False
    if is_likely_previous_output(name):
        return False
    if name.startswith("."):
        return False
    return True


def is_likely_previous_output(name: str) -> bool:
    if re.match(r"^(merged(?:[_-]output)?|output)(?:[_-]\d+)?(?:\.[^.]+)?$", name):
        return True
    if re.match(r"^.+[_-]merged(?:[_-]\d+)?(?:\.[^.]+)?$", name):
        return True
    return False


def scan_files(folder: Path) -> list[Path]:
    return sorted(
        [path for path in folder.iterdir() if is_candidate_file(path)],
        key=natural_sort_key,
    )


def unique_by_files(candidates: Iterable[Candidate]) -> list[Candidate]:
    seen: set[tuple[str, ...]] = set()
    unique: list[Candidate] = []
    for candidate in sorted(candidates, key=lambda item: (-item.priority, item.label)):
        key = tuple(str(path.resolve()).lower() for path in candidate.files)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def detect_candidates(files: list[Path]) -> list[Candidate]:
    candidates: list[Candidate] = []

    extension_groups: dict[str, list[Path]] = {}
    for path in files:
        if path.suffix:
            extension_groups.setdefault(path.suffix.lower(), []).append(path)

    for suffix, group in extension_groups.items():
        if len(group) >= 2:
            ordered = sorted(group, key=natural_sort_key)
            candidates.append(
                Candidate(
                    label=f"{suffix} ({len(ordered)} files)",
                    files=ordered,
                    output_name=f"merged{suffix}",
                    source=f"extension {suffix}",
                    priority=80 + len(ordered),
                )
            )

    numbered_groups: dict[str, list[Path]] = {}
    for path in files:
        match = re.search(r"^(?P<base>.+)\.(?P<num>\d{2,})$", path.name)
        if match:
            numbered_groups.setdefault(match.group("base"), []).append(path)

    for base_name, group in numbered_groups.items():
        if len(group) >= 2:
            ordered = sorted(group, key=numbered_suffix_key)
            candidates.append(
                Candidate(
                    label=f"{base_name}.### ({len(ordered)} files)",
                    files=ordered,
                    output_name=base_name,
                    source=f"numbered sequence {base_name}.###",
                    priority=90 + len(ordered),
                )
            )

    stem_number_groups: dict[tuple[str, str], list[Path]] = {}
    stem_number_pattern = re.compile(
        r"^(?P<base>.+?)[._-](?P<num>\d+)(?P<suffix>\.[^.]+)$",
        re.IGNORECASE,
    )
    for path in files:
        match = stem_number_pattern.match(path.name)
        if not match:
            continue
        base = match.group("base")
        suffix = match.group("suffix").lower()
        stem_number_groups.setdefault((base, suffix), []).append(path)

    for (base_name, suffix), group in stem_number_groups.items():
        if len(group) >= 2:
            ordered = sorted(group, key=natural_sort_key)
            candidates.append(
                Candidate(
                    label=f"{base_name}_# {suffix} ({len(ordered)} files)",
                    files=ordered,
                    output_name=f"{base_name}{suffix}",
                    source="numbered filename sequence",
                    priority=95 + len(ordered),
                )
            )

    part_marker_groups: dict[tuple[str, str], list[Path]] = {}
    marker_pattern = re.compile(
        r"^(?P<prefix>.*?)(?:[._ -]?part|[._ -]?pt)(?P<num>\d+)(?P<suffix>\.[^.]+)?$",
        re.IGNORECASE,
    )
    for path in files:
        match = marker_pattern.match(path.name)
        if not match:
            continue
        prefix = (match.group("prefix") or "").strip("._- ")
        suffix = match.group("suffix") or ""
        part_marker_groups.setdefault((prefix, suffix.lower()), []).append(path)

    for (prefix, suffix), group in part_marker_groups.items():
        if len(group) >= 2:
            ordered = sorted(group, key=natural_sort_key)
            output_prefix = prefix or "merged"
            output_name = f"{output_prefix}_merged{suffix}" if prefix else f"merged{suffix}"
            candidates.append(
                Candidate(
                    label=f"{prefix or 'part'}*{suffix} ({len(ordered)} files)",
                    files=ordered,
                    output_name=output_name,
                    source="part-numbered names",
                    priority=70 + len(ordered),
                )
            )

    return unique_by_files(candidates)


def choose_candidate(
    folder: Path,
    candidates: list[Candidate],
    theme: Theme,
    assume_yes: bool,
) -> Optional[Candidate]:
    if not candidates:
        return None

    extension_candidates = [item for item in candidates if item.source.startswith("extension")]
    obvious_extensions = [item for item in extension_candidates if len(item.files) >= 2]

    if len(obvious_extensions) == 1:
        return obvious_extensions[0]

    if len(candidates) == 1:
        return candidates[0]

    if assume_yes or not sys.stdin.isatty():
        return sorted(candidates, key=lambda item: (-len(item.files), -item.priority))[0]

    print(theme.yellow("Multiple file groups detected."))
    print()
    for index, candidate in enumerate(candidates, start=1):
        size = sum(path.stat().st_size for path in candidate.files)
        print(f"{index}) {candidate.label} - {format_size(size)}")
    print()

    while True:
        answer = input("Choose: ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(candidates):
            return candidates[int(answer) - 1]
        print(theme.red("Enter one of the listed numbers."))


def files_from_pattern(folder: Path, pattern: str) -> list[Path]:
    return sorted(
        [path for path in folder.glob(pattern) if is_candidate_file(path)],
        key=natural_sort_key,
    )


def choose_output_path(
    folder: Path,
    candidate: Candidate,
    requested_output: Optional[str],
    overwrite: bool,
) -> tuple[Path, bool]:
    if requested_output:
        return (folder / requested_output).resolve(), False

    output = (folder / candidate.output_name).resolve()
    if overwrite or not output.exists():
        return output, False

    stem = output.stem
    suffix = output.suffix
    for index in range(2, 1000):
        next_output = output.with_name(f"{stem}_{index}{suffix}")
        if not next_output.exists():
            return next_output.resolve(), True

    return output.with_name(f"{stem}_{int(time.time())}{suffix}").resolve(), True


def safe_filename(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name.strip())
    return cleaned.strip(". ") or "merged_output.bin"


def prompt_for_output_path(
    folder: Path,
    output_path: Path,
    theme: Theme,
    args: argparse.Namespace,
) -> tuple[Path, bool]:
    if args.output or args.yes or args.dry_run or not sys.stdin.isatty():
        return output_path, False

    print("Output filename:")
    answer = input(f"[{output_path.name}] ").strip()
    print()

    if not answer:
        return output_path, False

    renamed_path = (folder / safe_filename(answer)).resolve()
    if renamed_path.exists() and not args.overwrite:
        stem = renamed_path.stem
        suffix = renamed_path.suffix
        for index in range(2, 1000):
            next_path = renamed_path.with_name(f"{stem}_{index}{suffix}")
            if not next_path.exists():
                print(theme.yellow(f"That file exists, so using {next_path.name} instead."))
                print()
                return next_path.resolve(), True

    return renamed_path, True


def inspect_part_set(files: list[Path]) -> list[str]:
    warnings: list[str] = []
    number_infos = [
        NumberInfo(path=path, number=number)
        for path in files
        if (number := extract_part_number(path)) is not None
    ]

    if len(number_infos) == len(files):
        numbers = [info.number for info in number_infos]
        duplicates = sorted({number for number in numbers if numbers.count(number) > 1})
        if duplicates:
            warnings.append(
                "Duplicate part numbers detected: "
                + ", ".join(str(number) for number in duplicates)
            )

        unique_numbers = sorted(set(numbers))
        expected_numbers = list(range(unique_numbers[0], unique_numbers[-1] + 1))
        missing = [number for number in expected_numbers if number not in unique_numbers]
        if missing:
            warnings.append(
                "Missing part number(s): " + ", ".join(str(number) for number in missing)
            )

        if unique_numbers[0] not in {0, 1}:
            warnings.append(f"Numbering starts at {unique_numbers[0]}, not 0 or 1.")

    elif number_infos:
        warnings.append("Only some files have detectable part numbers.")

    sizes = [path.stat().st_size for path in files]
    if len(sizes) >= 3:
        largest_size = max(sizes)
        if largest_size > 0:
            for index, (path, size) in enumerate(zip(files, sizes), start=1):
                is_last = index == len(files)
                is_small = size < largest_size * 0.75
                if is_small and not is_last:
                    warnings.append(
                        f"{path.name} is much smaller than the largest part, "
                        "but it is not last."
                    )
                if size == 0:
                    warnings.append(f"{path.name} is empty.")

    return warnings


def print_scan_result(
    folder: Path,
    candidate: Candidate,
    output_path: Path,
    renamed_output: bool,
    theme: Theme,
) -> None:
    total_size = sum(path.stat().st_size for path in candidate.files)
    suffixes = sorted({path.suffix.lower() or "(none)" for path in candidate.files})

    print(f"Scanning folder: {display_path(folder)}")
    print()
    if len(suffixes) == 1:
        print(f"Detected extension: {theme.cyan(suffixes[0])}")
    else:
        print(f"Detected group: {theme.cyan(candidate.label)}")
    print(f"Found {theme.green(str(len(candidate.files)))} matching files")
    print()

    part_count = len(candidate.files)
    for index, path in enumerate(candidate.files, start=1):
        size = format_size(path.stat().st_size)
        print(f"{theme.green(SYMBOLS['check'])} {index}/{part_count} {path.name} ({size})")

    print()
    print(f"Combined size: {theme.bold(format_size(total_size))}")
    print()
    print("Output:")
    print(theme.cyan(output_path.name))
    if renamed_output:
        print(theme.yellow("Existing output detected, so a unique name was chosen."))
    print()

    warnings = inspect_part_set(candidate.files)
    if warnings:
        print(theme.yellow("Pre-flight warnings:"))
        for warning in warnings:
            print(theme.yellow(f"! {warning}"))
        print()
        print("If this looks wrong, stop now and fix the files before merging.")
        print()


class LiveDisplay:
    def __init__(self, theme: Theme):
        self.theme = theme
        self.lines_printed = 0
        self.live = sys.stdout.isatty()

    def render(
        self,
        part_index: int,
        part_count: int,
        file_name: str,
        file_size: int,
        file_done: int,
        total_done: int,
        total_size: int,
        started_at: float,
    ) -> None:
        elapsed = max(time.time() - started_at, 0.001)
        speed = total_done / elapsed
        remaining = (total_size - total_done) / speed if speed > 0 else 0

        lines = [
            separator(),
            f"Part {part_index} of {part_count}",
            f"File: {file_name}",
            f"Size: {format_size(file_size)}",
            separator(),
            "",
            self.theme.cyan(progress_bar(file_done, file_size)),
            "",
            "Current file:",
            f"{format_size(file_done)} / {format_size(file_size)}",
            "",
            "Overall:",
            f"{format_size(total_done)} / {format_size(total_size)}",
            "",
            "Speed:",
            f"{format_size(speed)}/s",
            "",
            "Elapsed:",
            format_duration(elapsed),
            "",
            "Estimated remaining:",
            format_duration(remaining),
        ]

        if self.live and self.lines_printed:
            sys.stdout.write(f"\033[{self.lines_printed}F")

        for line in lines:
            if self.live:
                sys.stdout.write("\033[2K")
            print(line)

        self.lines_printed = len(lines)
        sys.stdout.flush()

    def finish_block(self) -> None:
        if self.lines_printed:
            print()
            self.lines_printed = 0


def merge_files(
    files: list[Path],
    output_path: Path,
    overwrite: bool,
    calculate_hash: bool,
    theme: Theme,
    dry_run: bool,
    assume_yes: bool,
) -> int:
    if len(files) < 2:
        print(theme.red("Error: need at least 2 files to merge."))
        return 1

    files = [path for path in files if path.resolve() != output_path.resolve()]
    if len(files) < 2:
        print(theme.red("Error: output file was part of the detected input set."))
        return 1

    if output_path.exists() and not overwrite and not dry_run:
        print(theme.red(f"Error: output already exists: {output_path.name}"))
        print("Use --overwrite or choose a different --output filename.")
        return 1

    total_size = sum(path.stat().st_size for path in files)

    if dry_run:
        print("Dry run complete. No file was written.")
        return 0

    print("Ready.")
    print()
    if assume_yes:
        print("Starting now.")
    elif sys.stdin.isatty():
        input("Press ENTER to begin.")
    else:
        print("Non-interactive terminal detected; starting now.")
    print()

    started_at = time.time()
    bytes_written = 0
    display = LiveDisplay(theme)
    last_render = 0.0
    part_times: list[float] = []

    try:
        with output_path.open("wb") as outfile:
            for part_index, input_path in enumerate(files, start=1):
                part_started = time.time()
                file_size = input_path.stat().st_size
                file_done = 0

                display.render(
                    part_index,
                    len(files),
                    input_path.name,
                    file_size,
                    file_done,
                    bytes_written,
                    total_size,
                    started_at,
                )

                with input_path.open("rb") as infile:
                    while True:
                        chunk = infile.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        outfile.write(chunk)
                        chunk_size = len(chunk)
                        file_done += chunk_size
                        bytes_written += chunk_size

                        now = time.time()
                        if now - last_render >= 1:
                            display.render(
                                part_index,
                                len(files),
                                input_path.name,
                                file_size,
                                file_done,
                                bytes_written,
                                total_size,
                                started_at,
                            )
                            last_render = now

                display.render(
                    part_index,
                    len(files),
                    input_path.name,
                    file_size,
                    file_done,
                    bytes_written,
                    total_size,
                    started_at,
                )
                display.finish_block()

                part_elapsed = time.time() - part_started
                part_times.append(part_elapsed)
                print(theme.green(f"{SYMBOLS['check']} Finished {input_path.name}"))
                print(f"Time: {part_elapsed:.1f} seconds")
                print()

    except KeyboardInterrupt:
        display.finish_block()
        print(theme.yellow("Cancelled by user."))
        print("A partial output file may exist and should usually be deleted.")
        return 130
    except OSError as error:
        display.finish_block()
        print(theme.red(f"File error: {error}"))
        return 1

    elapsed = max(time.time() - started_at, 0.001)
    final_size = output_path.stat().st_size
    average_speed = final_size / elapsed

    print(separator())
    print(theme.bold("Merge complete"))
    print(separator())
    print()
    print("Output:")
    print(output_path.name)
    print()
    print("Size:")
    print(format_size(final_size))
    print()
    print("Verified:")
    if final_size == total_size:
        print(theme.green(f"{SYMBOLS['check']} Output size matches expected size"))
    else:
        print(theme.red("Output size does not match expected size"))
        return 2
    print()
    print("Average speed:")
    print(f"{format_size(average_speed)}/s")
    print()
    print("Time:")
    print(human_time(elapsed))

    if calculate_hash:
        print()
        print("SHA-256:")
        print(calculate_sha256(output_path))

    print()
    print("Done.")
    return 0


def choose_app_folder(args: argparse.Namespace, theme: Theme) -> tuple[Optional[Path], int]:
    ensure_standard_folders()
    demo_folder = PROJECT_ROOT / DEMO_FOLDER_NAME
    real_folder = PROJECT_ROOT / REAL_FOLDER_NAME

    if args.demo:
        return demo_folder.resolve(), 0

    if args.real:
        return real_folder.resolve(), 0

    if args.folder:
        return Path(args.folder).expanduser().resolve(), 0

    if not sys.stdin.isatty():
        return real_folder.resolve(), 0

    print("Choose what to merge:")
    print()
    print("1) Real files")
    print(f"   Put your real split files in: {display_path(real_folder)}")
    print()
    print("2) Demo files")
    print(f"   Uses the tiny sample parts in: {display_path(demo_folder)}")
    print()
    print("3) This folder")
    print(f"   Uses: {friendly_folder_name(Path.cwd())}")
    print()

    while True:
        answer = input("Choose [1]: ").strip() or "1"
        if answer == "1":
            return real_folder.resolve(), 0
        if answer == "2":
            return demo_folder.resolve(), 0
        if answer == "3":
            return Path.cwd().resolve(), 0
        print(theme.red("Enter 1, 2, or 3."))


def build_selection(args: argparse.Namespace, theme: Theme) -> tuple[Optional[list[Path]], Optional[Path], bool, int]:
    folder, folder_status = choose_app_folder(args, theme)
    if folder_status != 0 or folder is None:
        return None, None, False, folder_status

    if not folder.exists():
        print(theme.red(f"Error: folder does not exist: {folder}"))
        return None, None, False, 1
    if not folder.is_dir():
        print(theme.red(f"Error: path is not a folder: {folder}"))
        return None, None, False, 1

    if args.pattern:
        files = files_from_pattern(folder, args.pattern)
        if len(files) < 2:
            print(theme.red(f'Error: pattern "{args.pattern}" matched fewer than 2 files.'))
            return None, None, False, 1
        candidate = Candidate(
            label=f'{args.pattern} ({len(files)} files)',
            files=files,
            output_name=args.output or default_output_from_files(files),
            source="pattern",
            priority=100,
        )
    else:
        files = scan_files(folder)
        candidates = detect_candidates(files)
        candidate = choose_candidate(folder, candidates, theme, args.yes)
        if candidate is None:
            print(theme.red("Error: could not find an obvious group of split files."))
            print()
            if folder.name == REAL_FOLDER_NAME:
                print("For real files:")
                print(f"  1. Put all split parts in: {display_path(folder)}")
                print("  2. Run: py merge_parts.py")
                print()
            print("Or try one of these:")
            print('  py merge_parts.py --pattern "*.pkg"')
            print('  py merge_parts.py --pattern "*.001"')
            print('  py merge_parts.py --pattern "part*"')
            return None, None, False, 1

    output_path, renamed_output = choose_output_path(
        folder=folder,
        candidate=candidate,
        requested_output=args.output,
        overwrite=args.overwrite,
    )

    print_scan_result(folder, candidate, output_path, renamed_output, theme)
    output_path, user_renamed = prompt_for_output_path(folder, output_path, theme, args)
    if user_renamed:
        print("Output:")
        print(theme.cyan(output_path.name))
        print()
    return candidate.files, output_path, renamed_output, 0


def default_output_from_files(files: list[Path]) -> str:
    suffixes = {path.suffix.lower() for path in files if path.suffix}
    if len(suffixes) == 1:
        return f"merged{next(iter(suffixes))}"

    first = files[0].name
    numbered = re.match(r"^(?P<base>.+)\.\d{2,}$", first)
    if numbered:
        return numbered.group("base")

    return "merged_output.bin"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Auto-detect and merge .pkg, .001, .bin, and other split files.",
        epilog=(
            "Examples:\n"
            "  py merge_parts.py --real\n"
            "  py merge_parts.py --pattern \"*.pkg\"\n"
            "  py merge_parts.py --pattern \"*.001\"\n"
            "  py merge_parts.py --pattern \"*.bin\" --output merged.bin\n"
            "  py merge_parts.py \"D:\\MyParts\" --dry-run"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "folder",
        nargs="?",
        help="Folder containing split files. Bypasses the Demo/Real chooser.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--demo",
        action="store_true",
        help=f"Use the bundled {DEMO_FOLDER_NAME} folder.",
    )
    mode.add_argument(
        "--real",
        action="store_true",
        help=f"Use the {REAL_FOLDER_NAME} folder for real files.",
    )
    parser.add_argument(
        "-p",
        "--pattern",
        help='Optional glob pattern, for example "*.pkg", "*.001", or "part*".',
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output filename. Defaults to merged<extension> when possible.",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip the final Enter prompt and start immediately.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the output file if it exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show detection, order, and output name without writing a file.",
    )
    parser.add_argument(
        "--sha256",
        action="store_true",
        help="Calculate SHA-256 after merging.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable terminal colors.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    enable_windows_ansi()
    use_color = not args.no_color and sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
    theme = Theme(use_color)

    print()
    print_header(theme)

    files, output_path, _renamed_output, status = build_selection(args, theme)
    if status != 0 or files is None or output_path is None:
        return status

    return merge_files(
        files=files,
        output_path=output_path,
        overwrite=args.overwrite,
        calculate_hash=args.sha256,
        theme=theme,
        dry_run=args.dry_run,
        assume_yes=args.yes,
    )


if __name__ == "__main__":
    raise SystemExit(main())
