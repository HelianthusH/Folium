import hashlib
import json
import os
import struct
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from desktop.archive import Card, Catalog, export, verify
from desktop.codec import decode, unpack

ROOT = Path(__file__).resolve().parents[1]
SID = "1234567890abcdef"

class CardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.folder = self.root / "REC/2026/11/24" / SID
        self.folder.mkdir(parents=True)
        self.wav = self.folder / "0001.wav"
        with wave.open(str(self.wav), "wb") as w:
            w.setparams((1,2,16000,0,"NONE",""))
            w.writeframes(bytes(64000))
        self.meta = dict(session_id=SID, segment=1, file=self.wav.name, rate=16000, channels=1,
                         codec="pcm16", samples=32000, utc=1795564799, bytes=self.wav.stat().st_size,
                         sha256=hashlib.sha256(self.wav.read_bytes()).hexdigest())
        self.wav.with_suffix(".json").write_text(json.dumps(self.meta))
        self.source = Card(self.root)
        self.index = Catalog(":memory:")
        self.addCleanup(self.index.db.close)
        self.index.rebuild(self.source)

    def test_rebuild_and_interval(self):
        for _ in range(2):
            self.index.rebuild(self.source)
            self.assertEqual(len(self.index.select(SID,1795564800,1795564801)),1)
            self.assertEqual(self.index.select(SID,1795564801,None),[])
            self.assertEqual(self.index.select("0000000000000000"),[])

    def test_export_resume_and_verify(self):
        rows=self.index.select()
        class Disconnect(Card):
            def read(self,path,offset,limit=720):
                if offset>0:raise ConnectionError("LINK_LOST")
                return super().read(path,offset,limit)
        dest=self.root/"exports"
        with self.assertRaises(ConnectionError):export(Disconnect(self.root),rows,dest)
        staged=next(dest.rglob("*.wav"))
        self.assertEqual(staged.stat().st_size,720)
        final=export(self.source,rows,dest)
        self.assertEqual(verify(final),1)
        self.assertEqual(export(self.source,rows,dest),final)
        with (final/SID/self.wav.name).open("r+b") as f:f.write(b"x")
        with self.assertRaisesRegex(ValueError,"CORRUPT"):verify(final)

    def test_corrupt_source_quarantined(self):
        with self.wav.open("r+b") as f:f.seek(60);f.write(b"x")
        with self.assertRaisesRegex(ValueError,"CORRUPT"):export(self.source,self.index.select(),self.root/"dest")
        self.assertTrue(list((self.root/"dest").rglob("*.corrupt")))
        self.assertTrue(self.wav.exists())

    def test_path_escape(self):
        with self.assertRaisesRegex(ValueError,"INVALID"):self.source.local("../outside")

    def test_bad_metadata(self):
        self.meta["bytes"]+=1
        self.wav.with_suffix(".json").write_text(json.dumps(self.meta))
        with self.assertRaisesRegex(ValueError,"CORRUPT"):self.index.rebuild(self.source)

    def test_unsynced(self):
        self.meta["utc"]=0
        self.wav.with_suffix(".json").write_text(json.dumps(self.meta))
        self.index.rebuild(self.source)
        self.assertEqual(len(self.index.select(SID)),1)
        self.assertEqual(self.index.select(since=0),[])

class AudioTests(unittest.TestCase):
    def test_decoder(self):
        self.assertEqual(list(decode(bytes(256))),[0]*505)
        with self.assertRaises(ValueError):decode(bytes(255))
        with self.assertRaises(ValueError):decode(bytes([0,0,89])+bytes(253))

    def test_transmission_crc(self):
        import base64,zlib
        b=bytes(256);payload=base64.b64encode(b).decode()
        uid,pos,pcm=unpack(f"A {SID} 0123 505 {zlib.crc32(b):08x} {payload}")
        self.assertEqual((uid,pos,len(pcm)),(SID+"-0123",505,505))
        with self.assertRaisesRegex(ValueError,"CORRUPT"):unpack(f"A {SID} 0123 505 00000000 {payload}")

@unittest.skipUnless(os.name=="nt","Windows host")
class WindowsTests(unittest.TestCase):
    def test_pipe(self):
        import time,uuid
        from desktop.ipc import call,serve
        name="test-"+uuid.uuid4().hex
        serve(name,lambda req:req["message"])
        for i in range(50):
            try:
                self.assertEqual(call(name,{"message":"中文 {Enter}"}),"中文 {Enter}");return
            except OSError:
                if i==49:raise
                time.sleep(.05)

    def test_draft_and_replay(self):
        from desktop.adapters import Adapters,clean
        self.assertEqual(clean("草稿\n{Enter}\t文字"),"草稿 {Enter} 文字")
        with tempfile.TemporaryDirectory() as t:
            a=Adapters(Path(t)/"a.db",{})
            self.assertEqual(a.insert("missing","u1","语音"),"draft_saved")
            self.assertEqual(a.insert("missing","u1","语音"),"draft_saved")
            with self.assertRaisesRegex(ValueError,"ID_CONFLICT"):a.insert("missing","u1","不同")
            import sqlite3
            from contextlib import closing
            with closing(sqlite3.connect(a.db)) as db, db:db.execute("UPDATE drafts SET state='inserted'")
            self.assertEqual(a.insert("missing","u1","语音"),"already_inserted")

if __name__=="__main__":unittest.main()
