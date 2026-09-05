from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".json", ".toml", ".yml", ".yaml", ".md", ".txt"}
SECRET_PATTERNS = {
    "OpenAI-style secret": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Private key material": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}
ASSIGNMENT = re.compile(
    r"(?m)^[ \t]*(?:LLM_API_KEY|OPENAI_API_KEY|API_KEY|SECRET_KEY|ACCESS_TOKEN)"
    r"[ \t]*=[ \t]*([^ \t#\r\n][^\r\n#]*)$"
)


def source_files() -> tuple[list[Path], bool]:
    """Return files to inspect and whether they came from Git's tracked-file list."""
    try:
        output = subprocess.check_output(
            ["git", "ls-files", "-z"], cwd=ROOT, stderr=subprocess.DEVNULL
        )
        return (
            [ROOT / item.decode("utf-8") for item in output.split(b"\0") if item],
            True,
        )
    except (OSError, subprocess.CalledProcessError):
        # A source snapshot/archive may intentionally not contain .git metadata.
        # In that case inspect the source tree, but do not mislabel local-only
        # secret files such as .env as "tracked".
        return (
            [
                path
                for path in ROOT.rglob("*")
                if path.is_file()
                and ".git" not in path.parts
                and ".venv" not in path.parts
                and "node_modules" not in path.parts
                and ".next" not in path.parts
                and path.name != ".env"
            ],
            False,
        )


def main() -> None:
    findings: list[str] = []
    files, using_git = source_files()
    relative_names = {path.relative_to(ROOT).as_posix() for path in files if path.exists()}
    if using_git and ".env" in relative_names:
        findings.append(".env is tracked; secrets must remain untracked")

    for path in files:
        if not path.exists() or path.stat().st_size > 1_000_000:
            continue
        if path.suffix.casefold() not in TEXT_SUFFIXES and path.name != ".env.example":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = path.relative_to(ROOT).as_posix()
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{rel}: possible {label}")
        for match in ASSIGNMENT.finditer(text):
            value = match.group(1).strip().strip('"\'')
            if value and value not in {"changeme", "example", "placeholder"}:
                findings.append(f"{rel}: non-empty high-risk secret assignment")

    if findings:
        print("Milestone 8 security audit: FAIL")
        for finding in sorted(set(findings)):
            print(f"- {finding}")
        raise SystemExit(1)

    mode = "tracked files" if using_git else "source files (Git metadata unavailable)"
    print(f"Milestone 8 security audit: PASS ({len(files)} {mode} inspected)")


if __name__ == "__main__":
    main()
