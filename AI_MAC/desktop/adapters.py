import hashlib
from contextlib import closing
import re
import sqlite3
import threading
import unicodedata
import uuid
from pathlib import Path

def clean(text):
    return " ".join("".join(" " if unicodedata.category(c) in ("Cc","Cf","Zl","Zp") else c for c in text).split())

class Adapters:
    def __init__(self, db, executables):
        self.db=db
        self.executables=executables
        self.target=None
        self.lock=threading.RLock()
        with closing(sqlite3.connect(db)) as con, con:
            con.execute("CREATE TABLE IF NOT EXISTS drafts(id TEXT PRIMARY KEY,text TEXT,state TEXT,target TEXT)")
            con.execute("UPDATE drafts SET state='draft_saved' WHERE state='pending'")

    def focus(self, app):
        import comtypes
        import psutil
        import win32gui
        import win32process
        import uiautomation as auto
        comtypes.CoInitialize()
        hwnd=win32gui.GetForegroundWindow()
        _,pid=win32process.GetWindowThreadProcessId(hwnd)
        exe=Path(psutil.Process(pid).exe()).name.lower()
        if exe not in [x.lower() for x in self.executables[app]]: raise ValueError("TARGET_LOST")
        ctrl=auto.GetFocusedControl()
        if not ctrl or ctrl.ControlTypeName not in ("EditControl","DocumentControl") or ctrl.IsPassword:
            raise ValueError("INPUT_DENIED")
        if not ctrl.HasKeyboardFocus or not ctrl.IsEnabled or not ctrl.GetTextPattern():
            raise ValueError("INPUT_DENIED")
        return hwnd,pid,tuple(ctrl.GetRuntimeId()),ctrl

    def bind(self, app):
        from .ipc import call
        with self.lock:
            if app=="claude_code":
                target=call("claude",{"op":"bind"})
            else:
                target=self.focus(app)[:3]
            self.target=(uuid.uuid4().hex,app,target)
            return self.target[0]

    def insert(self, target_id, uid, text, allow=True):
        from .ipc import call
        text=clean(text)
        if not text or len(text)>24000: raise ValueError("INVALID")
        with self.lock,closing(sqlite3.connect(self.db)) as con,con:
            row=con.execute("SELECT text,state FROM drafts WHERE id=?",(uid,)).fetchone()
            if row:
                if row[0]!=text: raise ValueError("ID_CONFLICT")
                return "already_inserted" if row[1]=="inserted" else "draft_saved"
            con.execute("INSERT INTO drafts VALUES(?,?,?,?)",(uid,text,"pending",target_id))
            con.commit()
            state="draft_saved"
            try:
                if allow and self.target and target_id==self.target[0]:
                    _,app,bound=self.target
                    if app=="claude_code":
                        call("claude",{"op":"insert","target":bound,"text":text})
                    else:
                        hwnd,pid,runtime,ctrl=self.focus(app)
                        if (hwnd,pid,runtime)!=bound: raise ValueError("TARGET_LOST")
                        # Insert Unicode only. No keyboard shortcuts, clipboard or Return.
                        import win32gui
                        from .unicode_input import insert_literal
                        if hwnd!=win32gui.GetForegroundWindow() or not ctrl.HasKeyboardFocus: raise ValueError("TARGET_LOST")
                        insert_literal(text)
                    state="inserted"
            except Exception: pass
            con.execute("UPDATE drafts SET state=? WHERE id=?",(state,uid))
            return state

