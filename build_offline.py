#!/usr/bin/env python3
"""
把 index.html 打包成单文件离线版本 index-offline.html:
  - 内联 tone.min.js
  - 把所有 samples/**.mp3 替换为 data:audio/mpeg;base64,...
  - 替换 INSTRUMENTS 的 baseUrl/urls 为内联 data URI 字典
"""
import base64, os, re, json, pathlib

ROOT = pathlib.Path("/Users/xiayanji/ear-trainer")
SRC  = ROOT / "index.html"
OUT  = ROOT / "index-offline.html"
TONE = ROOT / "tone.min.js"
SAMPLES = ROOT / "samples"

html = SRC.read_text(encoding="utf-8")

# ---- 1) 内联 Tone.js ----
tone_src = TONE.read_text(encoding="utf-8")
html = html.replace(
    '<script src="https://unpkg.com/tone@14.8.49/build/Tone.js"></script>',
    f'<script>\n/* Tone.js 14.8.49 (inlined) */\n{tone_src}\n</script>'
)

# ---- 2) 读入所有 mp3 → base64 data URI ----
def as_data_uri(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    return "data:audio/mpeg;base64," + b64

# 扫描现有文件
inst_files = {}     # inst -> { file_basename -> data_uri }
for inst_dir in sorted(SAMPLES.iterdir()):
    if not inst_dir.is_dir(): continue
    for mp3 in sorted(inst_dir.glob("*.mp3")):
        inst_files.setdefault(inst_dir.name, {})[mp3.name] = as_data_uri(mp3)

print("inlined instruments:", {k:len(v) for k,v in inst_files.items()})

# ---- 3) 生成新的 INSTRUMENTS 对象（用 data URI 替代 url） ----
# 保持与原代码中 note→filename 的对应一致
INSTRUMENT_MAP = {
    "piano": {
        "label": "钢琴",
        "urls": {
            "A1":"A1.mp3","C2":"C2.mp3","D#2":"Ds2.mp3","F#2":"Fs2.mp3",
            "A2":"A2.mp3","C3":"C3.mp3","D#3":"Ds3.mp3","F#3":"Fs3.mp3",
            "A3":"A3.mp3","C4":"C4.mp3","D#4":"Ds4.mp3","F#4":"Fs4.mp3",
            "A4":"A4.mp3","C5":"C5.mp3","D#5":"Ds5.mp3","F#5":"Fs5.mp3",
            "A5":"A5.mp3","C6":"C6.mp3",
        }
    },
    "strings": {
        "label": "弦乐",
        "urls": {"A3":"A3.mp3","C4":"C4.mp3","E4":"E4.mp3","G4":"G4.mp3",
                 "A4":"A4.mp3","C5":"C5.mp3","E5":"E5.mp3","G5":"G5.mp3",
                 "A5":"A5.mp3","C6":"C6.mp3","E6":"E6.mp3"}
    },
    "flute": {
        "label": "长笛",
        "urls": {"A4":"A4.mp3","C5":"C5.mp3","E5":"E5.mp3",
                 "A5":"A5.mp3","C6":"C6.mp3","E6":"E6.mp3"}
    },
    "guitar": {
        "label": "吉他",
        "urls": {"E2":"E2.mp3","F2":"F2.mp3","G2":"G2.mp3","A2":"A2.mp3","B2":"B2.mp3",
                 "C3":"C3.mp3","D3":"D3.mp3","E3":"E3.mp3","F3":"F3.mp3","G3":"G3.mp3","A3":"A3.mp3","B3":"B3.mp3",
                 "C4":"C4.mp3","D4":"D4.mp3","E4":"E4.mp3","F4":"F4.mp3","G4":"G4.mp3","A4":"A4.mp3","B4":"B4.mp3",
                 "C5":"C5.mp3","D5":"D5.mp3"}
    },
    "synth": {
        "label": "合成器",
        "urls": {"C2":"C2.mp3","D2":"D2.mp3","F2":"F2.mp3","G2":"G2.mp3","A2":"A2.mp3",
                 "C3":"C3.mp3","D3":"D3.mp3","F3":"F3.mp3","G3":"G3.mp3","A3":"A3.mp3",
                 "C4":"C4.mp3","D4":"D4.mp3","G4":"G4.mp3","A4":"A4.mp3",
                 "C5":"C5.mp3","D5":"D5.mp3"}
    },
}

new_instruments = {}
total_missing = []
for inst, meta in INSTRUMENT_MAP.items():
    got = inst_files.get(inst, {})
    urls_inline = {}
    for note, fname in meta["urls"].items():
        if fname in got:
            urls_inline[note] = got[fname]   # data URI
        else:
            total_missing.append(f"{inst}/{fname}")
    new_instruments[inst] = {
        "label": meta["label"],
        "baseUrl": "",
        "urls": urls_inline,
    }
if total_missing:
    print("NOTE: skipping missing (Tone will interpolate):", total_missing)

# ---- 4) 替换原代码中的 INSTRUMENTS 块 ----
js_obj = "const INSTRUMENTS = " + json.dumps(new_instruments, ensure_ascii=False) + ";"

# 原代码 INSTRUMENTS 以 const INSTRUMENTS = { 开头，到一个匹配花括号闭合 };
# 用正则保守匹配
pattern = re.compile(r"const INSTRUMENTS\s*=\s*\{.*?\n\};", re.DOTALL)
if not pattern.search(html):
    raise RuntimeError("could not locate INSTRUMENTS block in index.html")
html_new = pattern.sub(js_obj, html, count=1)

# ---- 5) HEAD 探测不再需要（data URI 一定可用），给 filterAvailableUrls 短路 ----
head_probe_stub = """async function filterAvailableUrls(cfg){
  // offline build: urls already inlined as data URIs
  return Object.assign({}, cfg.urls);
}"""
html_new = re.sub(
    r"async function filterAvailableUrls\(cfg\)\{.*?\n\}",
    head_probe_stub,
    html_new,
    count=1,
    flags=re.DOTALL,
)

OUT.write_text(html_new, encoding="utf-8")
print(f"OK: wrote {OUT}  size={OUT.stat().st_size/1024/1024:.1f} MB")
