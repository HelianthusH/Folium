import argparse
import json
import os
import queue
import secrets
import sqlite3
import sys
import threading
import time
from pathlib import Path
from .archive import Card,Usb,Catalog,export,verify

ROOT=Path(sys.executable).parent if getattr(sys,"frozen",False) else Path(__file__).resolve().parents[1]
DATA=Path(os.getenv("LOCALAPPDATA",Path.home()))/"VoiceCard"
CONFIG=DATA/"voicecard.json"

def settings():
    DATA.mkdir(parents=True,exist_ok=True)
    if not CONFIG.exists(): CONFIG.write_bytes((ROOT/"config"/"voicecard.json").read_bytes())
    return json.loads(CONFIG.read_text("utf-8-sig"))

def catalog(source,args):
    index=Catalog(DATA/"sessions.sqlite3")
    try:
        index.rebuild(source)
        rows=index.select(args.get("session_id"),args.get("since"),args.get("until"))
        if args["op"]=="sessions.export":return str(export(source,rows,args["dest"]))
        page=int(args.get("page",0))
        return [m for _,m in rows[page*50:(page+1)*50]]
    finally:index.db.close()

def gui():
    os.chdir(ROOT)
    import tkinter as tk
    from tkinter import ttk
    import win32crypt
    from .adapters import Adapters
    from .ipc import serve
    from .transport import Link
    from .voice import Speech
    cfg=settings(); root=tk.Tk();root.title("VoiceCard · 语音输入")
    text=tk.StringVar(value="正在连接录音器");stat=tk.StringVar(value="")
    root.columnconfigure(0,weight=1)
    ttk.Label(root,textvariable=stat,wraplength=500).grid(sticky="w",padx=15,pady=8)
    ttk.Label(root,textvariable=text,wraplength=500,font=("Microsoft YaHei UI",13)).grid(sticky="w",padx=15,pady=8)
    q=queue.Queue(768);screen=queue.SimpleQueue()
    def display(s):screen.put(("text",s))
    def event(s):
        try:q.put_nowait(s)
        except queue.Full:
            try:q.get_nowait()
            except queue.Empty:pass
            try:q.put_nowait("! LINK_LOST")
            except queue.Full:pass
    secret=DATA/"binding.dpapi"
    token=win32crypt.CryptUnprotectData(secret.read_bytes(),None,None,None,0)[1].decode() if secret.exists() else ""
    adapters=Adapters(DATA/"drafts.sqlite3",cfg["executables"])
    link=Link(cfg,lambda:token,event)
    def handle(args):
        nonlocal token
        op=args["op"]
        if op=="device.bind":
            if cfg["transport"]!="usb":raise ValueError("AUTH_REQUIRED")
            t=secrets.token_hex(16);link.call("pair",t);token=t
            tmp=secret.with_suffix(".tmp");tmp.write_bytes(win32crypt.CryptProtectData(t.encode(),"VoiceCard",None,None,None,0));tmp.replace(secret)
            link.call("time",int(time.time()));link.call("sub");return "bound"
        if op=="device.status":
            d,s,sid,pos,free,utc,err=link.call("status").split()
            return dict(device_id=d,state=s,session_id=sid,first_free_sample=int(pos),free_bytes=int(free),utc=int(utc),clock_trusted=int(utc)>0,battery_percent=None,last_error=err)
        if op=="device.set_time":return link.call("time",int(args.get("utc",time.time())))
        if op=="record.start":return link.call("start",args.get("codec",cfg["codec"]),request_id=args.get("request_id"))
        if op=="record.stop":return link.call("stop",args.get("session_id") or handle({"op":"device.status"})["session_id"],request_id=args.get("request_id"))
        if op=="audio.subscribe":return link.call("sub")
        if op in ("sessions.list","sessions.export"):
            if cfg["transport"]!="usb": raise ValueError("USB_REQUIRED")
            return catalog(Usb(link.call),args)
        if op=="adapter.bind":return adapters.bind(args["app"])
        if op=="adapter.insert":return adapters.insert(args["target_id"],args["utterance_id"],args["text"])
        raise ValueError("INVALID")
    serve("control",handle)
    def worker():
        try:
            speech=Speech(ROOT/cfg["model_directory"],adapters,display)
            speech.replay_call=link.call
        except Exception as exc:speech=None;display(str(exc))
        while True:
            s=q.get()
            try:
                if s.startswith("! CONNECTED"):
                    screen.put(("status","已连接 · "+cfg["transport"].upper()))
                    if token:link.call("sub")
                    if token and speech:speech.reconnect()
                elif s.startswith("!"):
                    screen.put(("status",s[2:]))
                    if speech:speech.event(s)
                elif speech:speech.event(s)
            except Exception as exc:
                if speech and speech.stream: speech.intact=False
                screen.put(("status",str(exc)))
    threading.Thread(target=worker,daemon=True).start()
    def action(args,delay=0):
        def work():
            try:
                if delay:display("请在 4 秒内点击目标草稿输入框");time.sleep(delay)
                display(str(handle(args)))
            except Exception as exc:display(str(exc))
        threading.Thread(target=work,daemon=True).start()
    buttons=ttk.Frame(root);buttons.grid(sticky="w",padx=10,pady=6)
    for name,op in (("USB 绑定","device.bind"),("状态","device.status"),("录音","record.start"),("停止","record.stop")):
        ttk.Button(buttons,text=name,command=lambda o=op:action({"op":o})).pack(side="left")
    targets=ttk.Frame(root);targets.grid(sticky="w",padx=10,pady=6)
    for app in ("workbuddy","codex","claude_code"):
        ttk.Button(targets,text="绑定 "+app,command=lambda a=app:action({"op":"adapter.bind","app":a},4)).pack(side="left")
    def drafts():
        w=tk.Toplevel(root);w.title("已保存的草稿");t=tk.Text(w,wrap="word");t.pack(fill="both",expand=True)
        with sqlite3.connect(DATA/"drafts.sqlite3") as db:
            for value,state in db.execute("SELECT text,state FROM drafts ORDER BY rowid DESC LIMIT 100"):
                t.insert("end",state+"  "+value+"\n\n")
    ttk.Button(root,text="打开草稿记录",command=drafts).grid(sticky="w",padx=12,pady=6)
    def pump():
        while not screen.empty():
            kind,msg=screen.get()
            if kind=="show":root.deiconify()
            elif kind=="quit":root.destroy();return
            else:(text if kind=="text" else stat).set(msg)
        root.after(80,pump)
    import pystray
    from PIL import Image,ImageDraw
    img=Image.new("RGB",(32,32),"#10342e");ImageDraw.Draw(img).ellipse((9,6,23,24),fill="#6ce9b7")
    icon=pystray.Icon("VoiceCard",img,"VoiceCard",menu=pystray.Menu(pystray.MenuItem("打开助手",lambda:screen.put(("show","")),default=True),pystray.MenuItem("退出",lambda:screen.put(("quit","")))))
    threading.Thread(target=icon.run,daemon=True).start()
    root.protocol("WM_DELETE_WINDOW",root.withdraw);pump();root.mainloop();icon.stop()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("op",nargs="?",default="gui")
    for key in ("card","dest","codec","session-id","app","target-id","utterance-id","text","request-id"):
        parser.add_argument("--"+key)
    for key in ("since","until","utc","page"): parser.add_argument("--"+key,type=int)
    a={k:v for k,v in vars(parser.parse_args()).items() if v is not None}
    if a["op"]=="gui":return gui()
    if a["op"]=="claude":
        from .claude_terminal import main as terminal
        return terminal()
    settings()
    if a["op"]=="verify":result=verify(a["dest"])
    elif "card" in a and a["op"] in ("sessions.list","sessions.export"):result=catalog(Card(a["card"]),a)
    else:
        from .ipc import call
        result=call("control",a)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__":main()

