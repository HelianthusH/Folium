import asyncio
import queue
import threading
import time
import uuid

UUID = "4cb3000{}-7873-46d7-884a-b66c77636431"

class Link:
    def __init__(self, config, token, event):
        self.cfg, self.token, self.event = config,token,event
        self.pending={}
        self.lock=threading.Lock()
        self.ready=threading.Event()
        self.buffer=bytearray()
        self.tx=queue.Queue(32)
        self.generation=0
        threading.Thread(target=self.run,daemon=True).start()

    def receive(self, data):
        self.buffer.extend(data)
        if len(self.buffer)>32768:
            self.buffer.clear()
            self.event("! CORRUPT")
        while b"\n" in self.buffer:
            line,_,tail=self.buffer.partition(b"\n")
            self.buffer=bytearray(tail)
            try:
                text=line.decode("ascii").strip()
            except UnicodeError:
                self.event("! CORRUPT")
                continue
            if text.startswith("R "):
                _,key,response=text.split(" ",2)
                with self.lock:
                    q=self.pending.get(key)
                    if q and q.empty(): q.put_nowait(response)
            elif text.startswith(("A ","E ","B ")):
                self.event(text)

    def call(self, op, *args, request_id=None):
        if not self.ready.wait(2):
            raise ConnectionError("LINK_LOST")
        key=request_id or uuid.uuid4().hex
        if len(key)>32 or any(not str(s).isascii() or any(c.isspace() for c in str(s)) for s in (key,op,*args)):
            raise ValueError("INVALID")
        reply=queue.Queue(1)
        with self.lock:
            if key in self.pending: raise ValueError("BUSY")
            self.pending[key]=reply
        try:
            wire=(" ".join(("V1",key,self.token() or "-",op,*map(str,args)))+"\n").encode()
            self.tx.put((self.generation,wire),timeout=1)
            response=reply.get(timeout=5)
            status,_,value=response.partition(" ")
            if status!="OK": raise RuntimeError(value)
            return value
        except queue.Empty as exc:
            raise ConnectionError("LINK_LOST") from exc
        finally:
            with self.lock: self.pending.pop(key,None)

    def run(self):
        while True:
            try:
                if self.cfg["transport"]=="ble": asyncio.run(self.ble())
                else: self.serial()
            except Exception as exc:
                self.event("! LINK_LOST "+str(exc))
            finally:
                self.ready.clear()
                self.generation+=1
                self.buffer.clear()
            time.sleep(2)

    def up(self):
        self.ready.set()
        self.event("! CONNECTED")

    def serial(self):
        import serial
        from serial.tools.list_ports import comports
        port=self.cfg.get("port")
        if not port:
            ports=[p.device for p in comports() if p.vid==0x2FE3]
            if len(ports)!=1: raise OSError("请在配置中选择录音器的 COM 口")
            port=ports[0]
        with serial.Serial(port,115200,timeout=.015,write_timeout=1) as s:
            s.dtr=True
            self.up()
            while True:
                try:
                    generation,data=self.tx.get_nowait()
                    if generation==self.generation: s.write(data)
                except queue.Empty: pass
                self.receive(s.read(max(1,s.in_waiting)))

    async def ble(self):
        from bleak import BleakClient,BleakScanner
        addr=self.cfg.get("ble_address")
        dev=await BleakScanner.find_device_by_address(addr) if addr else await BleakScanner.find_device_by_name("VoiceCard")
        if not dev: raise OSError("未发现 VoiceCard")
        async with BleakClient(dev, pair=True, timeout=30) as client:
            await client.start_notify(UUID.format(2),lambda _,d:self.receive(d))
            self.up()
            while client.is_connected:
                try:
                    generation,data=self.tx.get_nowait()
                    if generation==self.generation:
                        for pos in range(0,len(data),20):
                            await client.write_gatt_char(UUID.format(1),data[pos:pos+20],response=True)
                except queue.Empty: await asyncio.sleep(.01)

