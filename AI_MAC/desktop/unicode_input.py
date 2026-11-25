"""One Win32 SendInput batch consisting exclusively of literal UTF-16 units."""
import ctypes as ct
from ctypes import wintypes as wt

class Keyboard(ct.Structure):
    _fields_=[("vk",wt.WORD),("scan",wt.WORD),("flags",wt.DWORD),("time",wt.DWORD),("extra",ct.c_size_t)]
class Mouse(ct.Structure):
    _fields_=[("x",wt.LONG),("y",wt.LONG),("data",wt.DWORD),("flags",wt.DWORD),("time",wt.DWORD),("extra",ct.c_size_t)]
class Payload(ct.Union):
    _fields_=[("key",Keyboard),("mouse",Mouse)]
class Input(ct.Structure):
    _fields_=[("kind",wt.DWORD),("payload",Payload)]
def insert_literal(text):
    raw=text.encode("utf-16-le")
    events=(Input*len(raw))()
    for i in range(0,len(raw),2):
        unit=int.from_bytes(raw[i:i+2],"little")
        for j in (0,1):
            events[i+j].kind=1
            events[i+j].payload.key=Keyboard(0,unit,4|(2*j),0,0)
    if ct.windll.user32.SendInput(len(events),events,ct.sizeof(Input))!=len(events):
        raise OSError("INPUT_DENIED")

