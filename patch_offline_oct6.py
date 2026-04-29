#!/usr/bin/env python3
"""把八度档位从 5 档扩到 6 档（新增 +3）。幂等。"""
import pathlib, sys
p = pathlib.Path("/Users/xiayanji/ear-trainer/index-offline.html")
html = p.read_text(encoding="utf-8")
orig_len = len(html)
changes = 0
def replace(old, new, label):
    global html, changes
    if old in html:
        html = html.replace(old, new, 1); changes += 1; print(f"✓ {label}")
    else:
        print(f"- {label}: not found / already migrated")

# 1) initial state
replace(
    'octs: [false,false,true,true,false],    // -2,-1,中央C,+1,+2；默认中央C和+1',
    'octs: [false,false,true,true,false,false],    // -2,-1,中央C,+1,+2,+3；默认中央C和+1',
    "initial state"
)

# 2) renderOct/updateOctLabel
old_block = '''const octBox = document.getElementById("octBox");
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
new_block = '''const octBox = document.getElementById("octBox");
const OCT_LABELS = ["−2", "−1", "中央C", "+1", "+2", "+3"];
function renderOct(){
  octBox.innerHTML = "";
  for (let k=0;k<6;k++){
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
  for (let k=0;k<6;k++) if (state.octs[k]) sel.push(OCT_LABELS[k]);
  document.getElementById("octLbl").textContent =
    sel.length ? sel.join(" · ") : "未选";
}
renderOct(); updateOctLabel();'''
replace(old_block, new_block, "renderOct/updateOctLabel")

# 3) pickSequence
replace(
    'const octs = []; for (let k=0;k<5;k++) if (state.octs[k]) octs.push(k-2);',
    'const octs = []; for (let k=0;k<6;k++) if (state.octs[k]) octs.push(k-2);',
    "pickSequence loop bound"
)

# 4) auditionDegree
replace(
    '  for (let k=0;k<5;k++) if (state.octs[k]){ oct = k-2; break; }',
    '  for (let k=0;k<6;k++) if (state.octs[k]){ oct = k-2; break; }',
    "auditionDegree loop bound"
)

if changes == 0:
    print("\nNothing to do."); sys.exit(0)
p.write_text(html, encoding="utf-8")
print(f"\n✓ wrote {p} ({orig_len} → {len(html)} bytes, {changes} edits)")
