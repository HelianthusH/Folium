"""Rebuildable local index and resumable, verified card/USB export."""
import base64
import hashlib
import json
import os
import re
import sqlite3
import zlib
from pathlib import Path, PurePosixPath

SID = re.compile(r"[0-9a-f]{16}")
DIGEST = re.compile(r"[0-9a-f]{64}")


class Card:
    def __init__(self, root):
        self.root = (Path(root) / "REC").resolve(strict=True)

    def local(self, name):
        p = (self.root / name).resolve()
        if not p.is_relative_to(self.root):
            raise ValueError("INVALID")
        return p

    def manifests(self):
        return (p.relative_to(self.root).as_posix() for p in self.root.rglob("*.json"))

    def read(self, path, offset, limit=65536):
        with self.local(path).open("rb") as f:
            f.seek(offset)
            return f.read(limit)


class Usb:
    def __init__(self, call):
        self.call = call

    def manifests(self):
        stack = ["."]
        while stack:
            folder = stack.pop()
            i = 0
            while True:
                item = self.call("ls", folder, str(i))
                if item == "END":
                    break
                kind, name = item.split(" ", 1)
                if not re.fullmatch(r"[A-Za-z0-9_.-]+", name) or name in (".", ".."):
                    raise ValueError("CORRUPT")
                p = str(PurePosixPath(folder, name))
                if kind == "D" and len(PurePosixPath(p).parts) <= 4:
                    stack.append(p)
                if kind == "F" and p.endswith(".json"):
                    yield p
                i += 1

    def read(self, path, offset, limit=720):
        reply = self.call("get", path, str(offset))
        crc, _, encoded = reply.partition(" ")
        chunk = base64.b64decode(encoded, validate=True)
        if zlib.crc32(chunk) != int(crc, 16):
            raise ValueError("CORRUPT")
        return chunk[:limit]


def manifest(source, path):
    buf = bytearray()
    while True:
        data = source.read(path, len(buf))
        if not data:
            break
        buf.extend(data)
        if len(buf) > 8192:
            raise ValueError("CORRUPT")
    m = json.loads(buf)
    if (not SID.fullmatch(m["session_id"]) or not DIGEST.fullmatch(m["sha256"])
            or m["rate"] != 16000 or m["channels"] != 1 or m["codec"] not in ("ima", "pcm16")
            or m["segment"] < 1 or not 0 <= m["samples"] <= 16000*301
            or m["file"] != f"{m['segment']:04d}.wav"
            or PurePosixPath(path).stem != f"{m['segment']:04d}"
            or PurePosixPath(path).parent.name != m["session_id"]):
        raise ValueError("CORRUPT " + path)
    expected = 44 + 2*m["samples"] if m["codec"] == "pcm16" else 60 + 256*((m["samples"]+504)//505)
    if expected != m["bytes"]:
        raise ValueError("CORRUPT " + path)
    return m


class Catalog:
    def __init__(self, db):
        self.db = sqlite3.connect(db)
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS segments(sid TEXT, part INTEGER, utc REAL, end REAL,
        path TEXT, meta TEXT, PRIMARY KEY(sid,part));
        CREATE INDEX IF NOT EXISTS time_range ON segments(utc,end);
        """)

    def rebuild(self, source):
        with self.db:
            self.db.execute("DELETE FROM segments")
            for path in source.manifests():
                m = manifest(source, path)
                self.db.execute("INSERT INTO segments VALUES(?,?,?,?,?,?)", (
                    m["session_id"], m["segment"], m["utc"], m["utc"]+m["samples"]/16000,
                    path, json.dumps(m, ensure_ascii=False)))

    def select(self, sid=None, since=None, until=None):
        sql = "SELECT path,meta FROM segments WHERE 1"
        args = []
        for condition, value in (("sid=?",sid),("utc>0 AND end>?",since),("utc>0 AND utc<?",until)):
            if value is not None:
                sql += " AND " + condition
                args.append(value)
        return [(p,json.loads(m)) for p,m in self.db.execute(sql+" ORDER BY utc,sid,part",args)]


def hashfile(path):
    sha = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(131072), b""):
            sha.update(chunk)
    return sha.hexdigest()


def export(source, rows, folder):
    target = Path(folder)
    if not rows:
        raise ValueError("NO_MATCH")
    target.mkdir(parents=True, exist_ok=True)
    batch = hashlib.sha256("".join(m["sha256"] for _,m in rows).encode()).hexdigest()[:16]
    final = target / ("export-"+batch)
    stage = target / (".partial-"+batch)
    if final.exists():
        verify(final)
        return final
    stage.mkdir(exist_ok=True)
    report = []
    for path, m in rows:
        rel = Path(m["session_id"]) / m["file"]
        dst = stage/rel
        dst.parent.mkdir(exist_ok=True)
        remote = str(PurePosixPath(path).with_suffix(".wav"))
        pos = dst.stat().st_size if dst.exists() else 0
        with dst.open("ab") as f:
            while pos < m["bytes"]:
                data = source.read(remote,pos)
                if not data or pos+len(data)>m["bytes"]:
                    raise IOError("EXPORT_FAILED " + remote)
                f.write(data)
                pos += len(data)
            f.flush()
            os.fsync(f.fileno())
        if pos!=m["bytes"] or hashfile(dst)!=m["sha256"] or source.read(remote,pos):
            dst.replace(dst.with_suffix(".corrupt"))
            raise ValueError("CORRUPT " + remote)
        dst.with_suffix(".json").write_text(json.dumps(m,indent=2),encoding="utf-8")
        report.append(dict(path=rel.as_posix(),bytes=pos,sha256=m["sha256"]))
    (stage/"SHA256.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    stage.rename(final)
    return final


def verify(folder):
    root = Path(folder).resolve()
    report = json.loads((root/"SHA256.json").read_text("utf-8"))
    if not report:
        raise ValueError("CORRUPT")
    for row in report:
        p=(root/row["path"]).resolve()
        if not p.is_relative_to(root) or p.stat().st_size!=row["bytes"] or hashfile(p)!=row["sha256"]:
            raise ValueError("CORRUPT " + row["path"])
    return len(report)

