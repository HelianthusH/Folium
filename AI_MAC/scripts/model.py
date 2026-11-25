"""Install the pinned bilingual CPU model from an archive or from upstream."""
import hashlib
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NAME="sherpa-onnx-streaming-zipformer-small-bilingual-zh-en-2023-02-16"
DIGEST="2b7c63322b32e5e0f2526043a1103366119ca58dd615cd7105a37c01db9553d7"
def install(archive, dest):
    sha=hashlib.sha256()
    with archive.open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):sha.update(block)
    if sha.hexdigest()!=DIGEST: raise ValueError("模型压缩包的 SHA-256 不匹配")
    files=["tokens.txt",*(part+"-epoch-99-avg-1.int8.onnx" for part in ("encoder","decoder","joiner")),"test_wavs/0.wav","test_wavs/1.wav","test_wavs/readme.md"]
    with tarfile.open(archive,"r|bz2") as tar:
        for member in tar:
            key=member.name.removeprefix(NAME+"/")
            if key not in files:continue
            target=dest/key;target.parent.mkdir(parents=True,exist_ok=True)
            temp=target.with_suffix(".part")
            with temp.open("wb") as out:shutil.copyfileobj(tar.extractfile(member),out)
            temp.replace(target);files.remove(key)
    if files:raise ValueError("模型缺少 "+str(files))
if __name__=="__main__":
    path=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/".build"/"model.tar.bz2"
    if not path.exists():
        path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_suffix(".download")
        urllib.request.urlretrieve("https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"+NAME+".tar.bz2",temp)
        temp.replace(path)
    install(path,ROOT/"models"/"bilingual")

