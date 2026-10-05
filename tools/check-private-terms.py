#!/usr/bin/env python3
"""Keep personal names and family details out of this repository.

The forbidden terms are stored only as SHA-256 hashes, so the check never
publishes the very words it exists to keep out. Text is lowercased and split
into words; every single word and every run of two or three words is hashed
and compared, so "Some Name", "some-name" and "some_name" all match.

Usage:
  tools/check-private-terms.py                 # every tracked text file
  tools/check-private-terms.py --commits RANGE # commit messages and authors in RANGE
  tools/check-private-terms.py --message FILE  # one commit message (commit-msg hook)
  tools/check-private-terms.py --staged        # staged files only (pre-commit hook)
  tools/check-private-terms.py --self-test

Extra terms that should not be published even as hashes can go, one per line,
in a `.private-terms` file at the repo root. That file is gitignored.

Exit status: 0 clean, 1 a term was found, 2 nothing was checked.
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

HASHES = {
    "d7ebc9cfd9f1b9f4e3dd9d40306bd8368cfe05b3ed38484e913cf194ff0604c0",
    "0ff74e67ba068e46c2d0efae9f9b1769e233460ccd4ad909314f7075d0e2aee8",
    "196105f31fd26354f5bd4152aa6f23bd2a085451082a0c5bdb7308c7bffc53f6",
    "d4c36e2c0a3b88c7a0eec395feff4a9043a6cdd93aa0e75ab897503501d5098a",
    "0b64bab80bc3a1717a4a6f1617290dcc91f6cb12c57cf4cc135e494cf0e77dad",
    "cd8b78cd37ac684d82e066c95ed6995446b9ffb3e3f5028092ff0248c0c37b79",
    "6fe8ecbc1deafa51c2ecf088cf364eba1ceba9032ffbe2621e771b90ea93153d",
    "0af145caafe1fe9bfe95960aac0deaf04b8f743c551da5d431ff1bdf2e61c98f",
    "569d7dc1611b50e40d5b898c212f4742e3b7d76996bac5d63739fef589f3ccc0",
    "88a1881f0025cf7117501d07aefc5d4be6696656790d765678df8bc48ca52687",
}
EXPECTED_HASHES = 10  # a list that quietly shrank would read as a pass

ROOT = Path(__file__).resolve().parent.parent
WORD = re.compile(r"[a-z0-9]+")


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def load_terms():
    hashes = set(HASHES)
    local = ROOT / ".private-terms"
    if local.exists():
        for line in local.read_text().splitlines():
            line = " ".join(WORD.findall(line.lower()))
            if line:
                hashes.add(sha(line))
    return hashes


def hits(text, hashes):
    words = WORD.findall(text.lower())
    found = 0
    for n in (1, 2, 3):
        for i in range(len(words) - n + 1):
            if sha(" ".join(words[i:i + n])) in hashes:
                found += 1
    return found


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def text_of(path):
    try:
        data = (ROOT / path).read_bytes()
    except (FileNotFoundError, IsADirectoryError):
        return None
    if b"\0" in data[:4096]:
        return None
    return data.decode("utf-8", errors="replace")


def check_files(paths, hashes):
    checked, bad = 0, []
    for path in paths:
        text = text_of(path)
        if text is None:
            continue
        checked += 1
        for lineno, line in enumerate(text.splitlines(), 1):
            if hits(line, hashes):
                bad.append(f"{path}:{lineno}")
        if hits(path, hashes):
            bad.append(f"{path} (file name)")
    return checked, bad


def check_commits(rng, hashes):
    out = git("log", "--format=%H%x00%an%x00%ae%x00%cn%x00%ce%x00%B%x1e", rng)
    checked, bad = 0, []
    for record in out.split("\x1e"):
        record = record.strip()
        if not record:
            continue
        checked += 1
        sha_, *rest = record.split("\x00")
        if hits(" ".join(rest), hashes):
            bad.append(f"commit {sha_[:12]}")
    return checked, bad


def self_test():
    probe = {sha("zzprobe"), sha("zz two words")}
    assert hits("nothing here", probe) == 0
    assert hits("a ZZProbe here", probe) == 1
    assert hits("zz-two_words", probe) == 1
    assert hits("zz two", probe) == 0
    assert len(HASHES) == EXPECTED_HASHES, "the term list changed size"
    print("self-test passed")
    return 0


def report(checked, bad, what):
    if checked == 0:
        print(f"check-private-terms: NOTHING CHECKED ({what}). This is not a pass.")
        return 2
    if bad:
        print(f"check-private-terms: {len(bad)} private term(s) found in {what}:")
        for b in bad:
            print(f"  {b}")
        print("Remove them. For a commit message, reword it (and amend or rebase if already committed).")
        return 1
    print(f"check-private-terms: clean ({checked} checked in {what})")
    return 0


def main(argv):
    hashes = load_terms()
    if "--self-test" in argv:
        return self_test()
    if len(HASHES) != EXPECTED_HASHES:
        print("check-private-terms: the hash list changed size; update EXPECTED_HASHES deliberately.")
        return 1
    if "--message" in argv:
        text = Path(argv[argv.index("--message") + 1]).read_text()
        text = "\n".join(l for l in text.splitlines() if not l.startswith("#"))
        return report(1, ["commit message"] if hits(text, hashes) else [], "the commit message")
    if "--commits" in argv:
        rng = argv[argv.index("--commits") + 1]
        checked, bad = check_commits(rng, hashes)
        return report(checked, bad, f"commits {rng}")
    if "--staged" in argv:
        paths = [p for p in git("diff", "--cached", "--name-only", "--diff-filter=ACMR").splitlines() if p]
        if not paths:
            return 0
        checked, bad = check_files(paths, hashes)
        return report(checked, bad, "staged files")
    paths = [p for p in git("ls-files").splitlines() if p]
    checked, bad = check_files(paths, hashes)
    return report(checked, bad, "tracked files")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
