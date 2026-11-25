"""Replay the two upstream test WAVs through the installed bilingual recognizer."""
import json
import sys
import wave
from pathlib import Path
from types import SimpleNamespace
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from desktop.voice import Speech
def run():
    model=ROOT/"models/bilingual"
    asr=Speech(model,SimpleNamespace(target=None),lambda s:None)
    results=[]
    for path in sorted((model/"test_wavs").glob("*.wav")):
        s=asr.r.create_stream()
        with wave.open(str(path)) as w:
            assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,16000)
            while data:=w.readframes(320):
                s.accept_waveform(16000,np.frombuffer(data,dtype="<i2").astype("float32")/32768)
                while asr.r.is_ready(s):asr.r.decode_stream(s)
        s.accept_waveform(16000,np.zeros(8000,dtype="float32"));s.input_finished()
        while asr.r.is_ready(s):asr.r.decode_stream(s)
        text=asr.r.get_result(s).strip()
        assert text,path
        results.append({"sample":path.name,"transcript":text})
    assert len(results)==2
    print(json.dumps(results,ensure_ascii=True,indent=2))
if __name__=="__main__":run()
