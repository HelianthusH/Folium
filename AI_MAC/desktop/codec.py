import base64
import struct
import zlib
from array import array

STEPS = (7,8,9,10,11,12,13,14,16,17,19,21,23,25,28,31,34,37,41,45,50,55,60,66,73,80,88,97,107,118,130,143,157,173,190,209,230,253,279,307,337,371,408,449,494,544,598,658,724,796,876,963,1060,1166,1282,1411,1552,1707,1878,2066,2272,2499,2749,3024,3327,3660,4026,4428,4871,5358,5894,6484,7132,7845,8630,9493,10442,11487,12635,13899,15289,16818,18500,20350,22385,24623,27086,29794,32767)
DELTA = (-1,-1,-1,-1,2,4,6,8)

def decode(block):
    if len(block)!=256:
        raise ValueError("CORRUPT")
    value, idx, reserved = struct.unpack_from("<hBB",block)
    if idx>88 or reserved:
        raise ValueError("CORRUPT")
    pcm = array("h",[value])
    for byte in block[4:]:
        for code in (byte&15,byte>>4):
            step=STEPS[idx]
            change=(step>>3)+(step if code&4 else 0)+(step>>1 if code&2 else 0)+(step>>2 if code&1 else 0)
            value=max(-32768,min(32767,value+(-change if code&8 else change)))
            idx=max(0,min(88,idx+DELTA[code&7]))
            pcm.append(value)
    return pcm

def unpack(line):
    _,sid,utterance,first,crc,payload=line.split()
    block=base64.b64decode(payload,validate=True)
    if zlib.crc32(block)!=int(crc,16):
        raise ValueError("CORRUPT")
    return sid+"-"+utterance,int(first),decode(block)

