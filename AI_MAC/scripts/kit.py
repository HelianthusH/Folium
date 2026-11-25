"""Build the portable kit and verify every archived member against its digest."""
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("README.md", "release/VoiceCard/VoiceCard.exe", "release/voicecard.uf2",
            "hardware/carrier/carrier-gerber.zip", "hardware/schematic/assembly.sch",
            "hardware/enclosure/base.stl", "hardware/enclosure/lid.stl",
            "release/VoiceCard/models/bilingual/tokens.txt")

def digest(stream):
    h = sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        h.update(block)
    return h.hexdigest()

def main():
    for name in REQUIRED:
        if not (ROOT / name).is_file():
            raise FileNotFoundError(name)
    files = [ROOT / n for n in ("README.md", "voicecard.py", "release/voicecard.uf2")]
    for directory in ("firmware", "desktop", "hardware", "config", "docs", "scripts",
                      "tests", "models", "release/VoiceCard"):
        files.extend(p for p in (ROOT / directory).rglob("*")
                     if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
    target = ROOT / "release/VoiceCard-Kit.zip"
    temp = target.with_suffix(".zip.part")
    hashes = {}
    with ZipFile(temp, "w", compression=ZIP_DEFLATED, compresslevel=3) as archive:
        for path in sorted(files):
            name = path.relative_to(ROOT).as_posix()
            with path.open("rb") as source:
                hashes[name] = digest(source)
            archive.write(path, name)
        archive.writestr("SHA256SUMS.txt", "".join(f"{h}  {n}\n" for n, h in hashes.items()))
    with ZipFile(temp) as archive:
        for name, expected in hashes.items():
            with archive.open(name) as content:
                if digest(content) != expected:
                    raise ValueError(name)
    temp.replace(target)
    with target.open("rb") as f:
        check = digest(f)
    target.with_suffix(".zip.sha256").write_text(f"{check}  {target.name}\n", encoding="ascii")
    print(f"{len(hashes)} files, {target.stat().st_size} bytes, SHA256 {check}")

if __name__ == "__main__":
    main()
