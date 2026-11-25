"""Feed one contiguous push-to-talk stream to the bilingual online recognizer."""
from pathlib import Path
import os
import numpy as np
from .codec import unpack

class Speech:
    def __init__(self, model, adapters, display):
        import sherpa_onnx
        folder=Path(model)
        # The Windows native runtime accepts ASCII filenames reliably. A relative
        # path also supports a Chinese installation directory on the same drive.
        if os.name=="nt":
            try: folder=Path(os.path.relpath(folder))
            except ValueError: pass
        def component(name):
            found=sorted(folder.glob(name+"*.onnx"),key=lambda p:("int8" not in p.name,p.name))
            if not found: raise FileNotFoundError("需要安装离线模型 "+str(folder))
            return str(found[0])
        self.r=sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=str(folder/"tokens.txt"),encoder=component("encoder"),decoder=component("decoder"),
            joiner=component("joiner"),num_threads=2,sample_rate=16000,feature_dim=80,
            decoding_method="greedy_search",enable_endpoint_detection=True,
            rule2_min_trailing_silence=0.8)
        self.adapters,self.display=adapters,display
        self.stream=None
        self.replay_call=None

    def recover_to(self,end):
        """Fill missing blocks of the open utterance using their sample offsets."""
        if self.expected >= end:
            return
        if not self.replay_call:
            self.intact=False
            return
        self.intact=False
        sid,utt=self.uid.split("-")
        while self.expected < end:
            first=self.expected
            payload=self.replay_call("block",self.uid,first)
            _,_,pcm=unpack(f"A {sid} {utt} {first} {payload}")
            self.accept(first,pcm[:min(505,end-first)])

    def reconnect(self):
        if self.stream is None or not self.replay_call:
            return
        uid,_,end,closed=self.replay_call("talk",self.uid).split()
        if uid!=self.uid:raise ValueError("RANGE_UNAVAILABLE")
        self.recover_to(int(end))
        if closed=="1": self.finish(False)

    def drain(self):
        while self.r.is_ready(self.stream): self.r.decode_stream(self.stream)
        return self.r.get_result(self.stream).strip()

    def finish(self, allowed):
        if self.stream is None: return
        self.stream.accept_waveform(16000,np.zeros(8000,dtype=np.float32))
        self.stream.input_finished()
        text=self.drain()
        if text:
            status=self.adapters.insert(self.target,self.uid+"-"+str(self.begin),text,allowed and self.intact)
            self.display(status+"  "+text)
        self.stream=None

    def event(self,line):
        if line.startswith("!"):
            if self.stream:self.intact=False
            return
        if line.startswith("B "):
            _,sid,utt,first=line.split()
            if self.stream:
                try:self.reconnect()
                finally:self.finish(False)
            self.new(sid+"-"+utt,int(first),True)
            return
        if line.startswith("E "):
            _,sid,utt,end=line.split()
            if self.stream and sid+"-"+utt==self.uid:
                self.recover_to(int(end))
                self.finish(self.expected-504<=int(end)<=self.expected)
            return
        uid,first,pcm=unpack(line)
        if self.stream is None or uid!=self.uid:
            self.finish(False)
            self.new(uid,first,False)
        if first<self.expected:return
        if first!=self.expected:self.recover_to(first)
        self.accept(first,pcm)

    def accept(self,first,pcm):
        self.expected=first+len(pcm)
        self.stream.accept_waveform(16000,np.asarray(pcm,dtype=np.float32)/32768)
        text=self.drain()
        if text:self.display(text)
        if self.r.is_endpoint(self.stream) and text:
            self.adapters.insert(self.target,self.uid+"-"+str(self.begin),text,self.intact)
            self.r.reset(self.stream)
            self.begin=self.expected

    def new(self,uid,first,intact):
        self.stream=self.r.create_stream()
        self.uid,self.begin,self.expected,self.intact=uid,first,first,intact
        self.target=self.adapters.target[0] if self.adapters.target else None

