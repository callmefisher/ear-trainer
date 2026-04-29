#!/usr/bin/env python3
"""对 index-offline.html 做节奏化改造，幂等运行。"""
import pathlib, re, sys

p = pathlib.Path("/Users/xiayanji/ear-trainer/index-offline.html")
html = p.read_text(encoding="utf-8")
orig_len = len(html)

changes = 0

# 1) 删掉音符间距 UI
old_ui = '''    <div class="group">
      <label>音色预设 <b id="timbreLbl">钢琴</b></label>
      <div class="timbre-grid" id="timbreBox"></div>
    </div>

    <div class="group">
      <label>音符间距 <b id="gapLbl">0.55s</b></label>
      <input type="range" id="gapRange" min="30" max="120" value="55" />
    </div>

  </section>'''
new_ui = '''    <div class="group">
      <label>音色预设 <b id="timbreLbl">钢琴</b></label>
      <div class="timbre-grid" id="timbreBox"></div>
    </div>

  </section>'''
if old_ui in html:
    html = html.replace(old_ui, new_ui, 1); changes += 1
    print("✓ removed gap UI block")
else:
    print("- gap UI block already removed (or not present)")

# 2) state.gap → state.tempo
old_state = 'timbre: "piano",\n  gap: 0.55,'
new_state = 'timbre: "piano",\n  tempo: 100,'
if old_state in html:
    html = html.replace(old_state, new_state, 1); changes += 1
    print("✓ replaced state.gap with state.tempo")
else:
    print("- state block already migrated")

# 3) 删除 gap 滑杆监听
old_listener = '''// 间距
const gapRange = document.getElementById("gapRange");
gapRange.addEventListener("input", ()=>{
  state.gap = +gapRange.value / 100;
  document.getElementById("gapLbl").textContent = state.gap.toFixed(2)+"s";
});'''
new_listener = '// 间距相关 UI 已移除；每轮节奏由 makeRhythm() 生成'
if old_listener in html:
    html = html.replace(old_listener, new_listener, 1); changes += 1
    print("✓ removed gap slider listener")
else:
    print("- gap slider listener already removed")

# 4) pickSequence → 带节奏
old_pick = '''function pickSequence(){
  const pool = []; for (let i=0;i<12;i++) if (state.pool[i]) pool.push(i);
  const octs = []; for (let k=0;k<5;k++) if (state.octs[k]) octs.push(k+1);
  if (!pool.length || !octs.length) return null;
  const seq = [];
  for (let i=0;i<state.noteCount;i++){
    seq.push({
      deg: pool[Math.floor(Math.random()*pool.length)],
      oct: octs[Math.floor(Math.random()*octs.length)],
    });
  }
  return seq;
}'''
new_pick = '''function pickSequence(){
  const pool = []; for (let i=0;i<12;i++) if (state.pool[i]) pool.push(i);
  const octs = []; for (let k=0;k<5;k++) if (state.octs[k]) octs.push(k+1);
  if (!pool.length || !octs.length) return null;
  const rhythm = makeRhythm(state.noteCount);
  const seq = [];
  for (let i=0;i<state.noteCount;i++){
    seq.push({
      deg: pool[Math.floor(Math.random()*pool.length)],
      oct: octs[Math.floor(Math.random()*octs.length)],
      dur: rhythm[i],
    });
  }
  return seq;
}

// 每轮用一个两小节（4/4）的模板采样节奏，保证律动自然
// 单位：1=四分，0.5=八分，1.5=附点四分，2=二分
function makeRhythm(n){
  const TEMPLATES = [
    [1, 1, 1, 1],
    [0.5, 0.5, 1, 1],
    [1, 0.5, 0.5, 1],
    [1.5, 0.5, 1, 1],
    [0.5, 0.5, 0.5, 0.5, 1, 1],
    [1, 1, 0.5, 0.5, 1],
    [2, 1, 1],
    [1, 2, 1],
    [0.5, 1, 0.5, 1, 1],
    [1, 0.5, 1.5],
    [0.75, 0.25, 1, 1],
    [1, 1, 0.5, 0.5, 0.5, 0.5],
  ];
  let picked = TEMPLATES[Math.floor(Math.random()*TEMPLATES.length)].slice();
  while (picked.length < n){
    let maxIdx = 0;
    for (let i=1;i<picked.length;i++) if (picked[i]>picked[maxIdx]) maxIdx = i;
    const v = picked[maxIdx] / 2;
    picked.splice(maxIdx, 1, v, v);
  }
  if (picked.length > n) picked = picked.slice(0, n);
  if (Math.random() < 0.5) picked[picked.length-1] *= 1.5;
  return picked;
}'''
if old_pick in html:
    html = html.replace(old_pick, new_pick, 1); changes += 1
    print("✓ upgraded pickSequence with rhythm")
else:
    print("- pickSequence already upgraded")

# 5) 替换 playAll 使用累积时间
old_play = '''async function playAll(){
  if (!state.sequence.length) return;
  await ensureAudio();
  if (!sampleReady){ toast("采样还在加载…"); return; }
  clearHighlights();
  const t0 = Tone.now() + 0.05;
  state.sequence.forEach((s,i)=>{
    const m = degreeToMidi(s.deg, s.oct);
    sampler.triggerAttackRelease(midiToNoteName(m), Math.max(0.3, state.gap-0.1), t0 + i*state.gap);
    setTimeout(()=>{
      clearHighlights();
      cardsEl.children[i]?.classList.add("playing");
    }, 20 + i*state.gap*1000);
  });
  setTimeout(clearHighlights, 20 + state.sequence.length*state.gap*1000 + 400);
  state.totalNotes += state.sequence.length;
  updateStats();
}'''
new_play = '''async function playAll(){
  if (!state.sequence.length) return;
  await ensureAudio();
  if (!sampleReady){ toast("采样还在加载…"); return; }
  clearHighlights();
  const beatSec = 60 / state.tempo;
  const t0 = Tone.now() + 0.05;
  let acc = 0;
  state.sequence.forEach((s,i)=>{
    const startRel = acc;
    const durSec = s.dur * beatSec;
    const playDur = Math.max(0.25, durSec * 0.92);
    const m = degreeToMidi(s.deg, s.oct);
    sampler.triggerAttackRelease(midiToNoteName(m), playDur, t0 + startRel);
    setTimeout(()=>{
      clearHighlights();
      cardsEl.children[i]?.classList.add("playing");
    }, 20 + startRel*1000);
    acc += durSec;
  });
  setTimeout(clearHighlights, 20 + acc*1000 + 400);
  state.totalNotes += state.sequence.length;
  updateStats();
}'''
if old_play in html:
    html = html.replace(old_play, new_play, 1); changes += 1
    print("✓ rewrote playAll to use rhythm schedule")
else:
    print("- playAll already upgraded")

if changes == 0:
    print("\nNothing to do: already up to date."); sys.exit(0)

p.write_text(html, encoding="utf-8")
print(f"\n✓ wrote {p} ({orig_len} → {len(html)} bytes, {changes} edits)")
