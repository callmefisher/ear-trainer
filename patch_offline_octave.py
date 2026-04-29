#!/usr/bin/env python3
"""把 index-offline.html 的八度表达从 '第 N' 改为以中央C为中心的 -2..+2 偏移。幂等。"""
import pathlib, sys

p = pathlib.Path("/Users/xiayanji/ear-trainer/index-offline.html")
html = p.read_text(encoding="utf-8")
orig_len = len(html)
changes = 0

def replace(old, new, label):
    global html, changes
    if old in html:
        html = html.replace(old, new, 1); changes += 1
        print(f"✓ {label}")
    else:
        print(f"- {label}: already migrated or not found")

# 1) 标签文案
replace(
    '<label>八度范围 <b id="octLbl">第 3 · 4</b></label>',
    '<label>八度范围 <b id="octLbl">中央C · +1</b></label>',
    "header label"
)

# 2) 初始状态
replace(
    'octs: [false,true,true,true,false],    // 第 2·3·4',
    'octs: [false,false,true,true,false],    // -2,-1,中央C,+1,+2；默认中央C和+1',
    "initial octs state"
)

# 3) renderOct + updateOctLabel
old_render = '''const octBox = document.getElementById("octBox");
function renderOct(){
  octBox.innerHTML = "";
  for (let k=1;k<=5;k++){
    const el = document.createElement("div");
    el.className = "oct" + (state.octs[k-1] ? " on":"");
    el.innerHTML = `<span>第</span><span class="num">${k}</span>`;
    el.addEventListener("click", ()=>{
      state.octs[k-1] = !state.octs[k-1];
      renderOct();
      updateOctLabel();
    });
    octBox.appendChild(el);
  }
}
function updateOctLabel(){
  const sel = [];
  for (let k=0;k<5;k++) if (state.octs[k]) sel.push(k+1);
  document.getElementById("octLbl").textContent =
    sel.length ? "第 "+sel.join(" · ") : "未选";
}
renderOct(); updateOctLabel();'''
new_render = '''const octBox = document.getElementById("octBox");
const OCT_LABELS = ["−2", "−1", "中央C", "+1", "+2"];
function renderOct(){
  octBox.innerHTML = "";
  for (let k=0;k<5;k++){
    const el = document.createElement("div");
    el.className = "oct" + (state.octs[k] ? " on":"");
    if (k===2){
      el.innerHTML = `<span class="num" style="font-size:13px; margin-top:4px; line-height:1.1;">中央C</span>`;
    } else {
      const offset = k - 2;
      el.innerHTML = `<span>${offset>0?"高":"低"}</span><span class="num">${offset>0?"+":""}${offset}</span>`;
    }
    el.addEventListener("click", ()=>{
      state.octs[k] = !state.octs[k];
      renderOct();
      updateOctLabel();
    });
    octBox.appendChild(el);
  }
}
function updateOctLabel(){
  const sel = [];
  for (let k=0;k<5;k++) if (state.octs[k]) sel.push(OCT_LABELS[k]);
  document.getElementById("octLbl").textContent =
    sel.length ? sel.join(" · ") : "未选";
}
renderOct(); updateOctLabel();'''
replace(old_render, new_render, "renderOct/updateOctLabel")

# 4) pickSequence 的 octs 推入
replace(
    'const octs = []; for (let k=0;k<5;k++) if (state.octs[k]) octs.push(k+1);',
    'const octs = []; for (let k=0;k<5;k++) if (state.octs[k]) octs.push(k-2);',
    "pickSequence octs"
)

# 5) auditionDegree
old_aud = '''function auditionDegree(i){
  if (!sampleReady) return;
  let oct = 4;
  for (let k=0;k<5;k++) if (state.octs[k]){ oct = k+1; break; }
  const m = degreeToMidi(i, oct);
  sampler.triggerAttackRelease(midiToNoteName(m), 0.6);
}'''
new_aud = '''function auditionDegree(i){
  if (!sampleReady) return;
  let oct = 0;
  for (let k=0;k<5;k++) if (state.octs[k]){ oct = k-2; break; }
  const m = degreeToMidi(i, oct);
  sampler.triggerAttackRelease(midiToNoteName(m), 0.6);
}'''
replace(old_aud, new_aud, "auditionDegree")

# 6) degreeToMidi 接口保持同名，但参数语义变为相对中央C的偏移
old_mid = '''function degreeToMidi(degIdx, oct){
  const keyPc = KEYS[state.keyIdx].pc;
  const semi = DEGREES[degIdx].off;
  return 12*(oct+1) + keyPc + semi;
}'''
new_mid = '''function degreeToMidi(degIdx, octOffset){
  const keyPc = KEYS[state.keyIdx].pc;
  const semi = DEGREES[degIdx].off;
  const midiOct = octOffset + 4;
  return 12*(midiOct+1) + keyPc + semi;
}'''
replace(old_mid, new_mid, "degreeToMidi")

# 7) 揭示卡片时的文案
replace(
    '+ `<span>第 ${s.oct} 度 · ${midiToNoteName(degreeToMidi(s.deg,s.oct))}</span>`;',
    '+ `<span>${s.oct===0?"中央C":"中央C"+(s.oct>0?"+":"")+s.oct} · ${midiToNoteName(degreeToMidi(s.deg,s.oct))}</span>`;',
    "reveal card octave label"
)

if changes == 0:
    print("\nNothing to do."); sys.exit(0)

p.write_text(html, encoding="utf-8")
print(f"\n✓ wrote {p} ({orig_len} → {len(html)} bytes, {changes} edits)")
