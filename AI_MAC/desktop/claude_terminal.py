"""An interactive dedicated Claude ConPTY. Its per-process pipe accepts draft text."""
import msvcrt
import os
import subprocess
import sys
import threading
import uuid
import shutil
import win32gui
from .adapters import clean
from .ipc import serve

def main():
    from winpty import PtyProcess
    exe=shutil.which("claude.exe") or shutil.which("claude")
    if not exe: raise SystemExit("未找到 claude，请先安装并登录 Claude Code")
    import winpty
    command=[os.environ["COMSPEC"],"/d","/c",exe] if exe.lower().endswith((".cmd",".bat")) else [exe]
    process=PtyProcess.spawn(subprocess.list2cmdline(command),backend=winpty.Backend.ConPTY)
    key=uuid.uuid4().hex
    # A new classic console is explicitly started by the launcher.
    import ctypes
    hwnd=ctypes.windll.kernel32.GetConsoleWindow()
    lock=threading.Lock()
    def handle(req):
        if req.get("op")=="bind" and process.isalive(): return key
        if req.get("op")!="insert" or req.get("target")!=key or not process.isalive() or win32gui.GetForegroundWindow()!=hwnd: raise ValueError("TARGET_LOST")
        with lock: process.write(clean(req["text"]))
        return "inserted"
    serve("claude",handle)
    def output():
        while process.isalive():
            try: sys.stdout.write(process.read(4096));sys.stdout.flush()
            except EOFError: break
    threading.Thread(target=output,daemon=True).start()
    arrows={"H":"\x1b[A","P":"\x1b[B","M":"\x1b[C","K":"\x1b[D","S":"\x1b[3~"}
    import time
    while process.isalive():
        if not msvcrt.kbhit():time.sleep(.012);continue
        c=msvcrt.getwch()
        if c in ("\x00","\xe0"):c=arrows.get(msvcrt.getwch(),"")
        if c:
            with lock: process.write(c)

