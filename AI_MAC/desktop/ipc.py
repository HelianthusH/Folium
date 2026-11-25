"""Length-bounded JSON on a local-only Windows pipe with an explicit user DACL."""
import json
import threading
import time
import win32api
import win32con
import win32file
import win32pipe
import win32security
import pywintypes

def identity():
    token=win32security.OpenProcessToken(win32api.GetCurrentProcess(),win32con.TOKEN_QUERY)
    return win32security.GetTokenInformation(token,win32security.TokenUser)[0]

def name(suffix):
    return r"\\.\pipe\VoiceCard-"+win32security.ConvertSidToStringSid(identity())+"-"+suffix

def security():
    acl=win32security.ACL()
    acl.AddAccessAllowedAce(win32security.ACL_REVISION,win32con.GENERIC_ALL,identity())
    sd=win32security.SECURITY_DESCRIPTOR()
    sd.SetSecurityDescriptorDacl(1,acl,0)
    sa=pywintypes.SECURITY_ATTRIBUTES()
    sa.SECURITY_DESCRIPTOR=sd
    return sa

def call(suffix, req):
    wire=json.dumps(req,ensure_ascii=False).encode()
    if len(wire)>60000: raise ValueError("INVALID")
    path=name(suffix)
    deadline=time.monotonic()+5
    while True:
        try:
            win32pipe.WaitNamedPipe(path,max(1,int(1000*(deadline-time.monotonic()))))
            h=win32file.CreateFile(path,win32con.GENERIC_READ|win32con.GENERIC_WRITE,0,None,win32con.OPEN_EXISTING,0,None)
            break
        except pywintypes.error as exc:
            if exc.winerror not in (2,231) or time.monotonic()>=deadline:raise
            time.sleep(.04)
    try:
        win32file.WriteFile(h,wire)
        data=win32file.ReadFile(h,65000)[1]
        res=json.loads(data)
        if not res["ok"]: raise RuntimeError(res["error"])
        return res["result"]
    finally: h.Close()

def serve(suffix, handler):
    def loop():
        sa=security()
        while True:
            h=win32pipe.CreateNamedPipe(name(suffix),win32pipe.PIPE_ACCESS_DUPLEX,
                win32pipe.PIPE_TYPE_MESSAGE|win32pipe.PIPE_READMODE_MESSAGE|0x8,1,65536,65536,5000,sa)
            try:
                try: win32pipe.ConnectNamedPipe(h,None)
                except pywintypes.error as e:
                    if e.winerror!=535: raise
                try:
                    request=json.loads(win32file.ReadFile(h,60000)[1])
                    result={"ok":True,"result":handler(request)}
                except Exception as exc: result={"ok":False,"error":str(exc)}
                wire=json.dumps(result,ensure_ascii=False).encode()
                if len(wire)>64000: wire=b'{"ok":false,"error":"LIMIT: narrow time range or paginate"}'
                win32file.WriteFile(h,wire)
                win32file.FlushFileBuffers(h)
            except pywintypes.error: pass
            finally: h.Close()
    threading.Thread(target=loop,daemon=True).start()

