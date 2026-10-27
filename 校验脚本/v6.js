/* 占比专项审计：分母口径 / 逐格复算 / 渲染文本 / 边界情况
   用法: node v6.js <订单文件> */
const fs = require("fs");
const path = require("path");
const { boot } = require("./boot.js");

const ORDERS = process.argv[2] || "C:/Users/Administrator/Desktop/10.27日服务商.xlsx";
const fname = path.basename(ORDERS);

let pass = 0, fail = 0;
const ok = (c, m) => { c ? pass++ : (fail++, console.log("  X " + m)); };
const eq = (a, b, m) => ok(a === b, m + "  期望=" + b + " 实际=" + a);

(async () => {
  const b = boot();
  b.sb.__raw = fs.readFileSync(ORDERS);
  b.run(`
    var wb=XLSX.read(new Uint8Array(__raw),{type:"array",cellDates:false});
    var sn=pickSheet(wb); var p=sheetToRows(wb.Sheets[sn]);
    globalThis.__rows=p.rows; globalThis.__sn=sn;
    process(p.rows, ${JSON.stringify(fname)}, sn);
  `);

  const BK = b.G("BLOCKS.map(x=>({key:x.key,name:x.name,level:x.level,codes:x.codes?Array.from(x.codes):null}))");
  const out = b.G("window.__exportData").filter(x => x.kind !== "header");

  /* ===== 1. 编码归属唯一性 ===== */
  console.log("== 1. 编码归属（一个编码只能属一个一级模块）==");
  const idxOf = (() => {
    const m = new Map();
    BK.forEach(x => { if (!x.codes) return; x.codes.forEach(c => { if (!m.has(c)) m.set(c, []); m.get(c).push(x.key); }); });
    return m;
  })();
  const level1 = BK.filter(x => x.level === 1).map(x => x.key);
  const crossModule = [];
  idxOf.forEach((keys, c) => {
    const mods = keys.filter(k => level1.includes(k));
    const parentOfKey = k => {
      const bl = BK.find(x => x.key === k);
      if (bl.level === 1) return k;
      const p = b.G("BLOCKS").find(x => x.key === k);
      return p && p.moduleKey ? p.moduleKey : k;
    };
    const roots = new Set(keys.map(parentOfKey));
    if (roots.size > 1) crossModule.push(c + "→" + [...roots].join("/"));
  });
  ok(crossModule.length === 0, "无编码跨一级模块：" + (crossModule.join(", ") || "无"));
  console.log("  编码总数 " + idxOf.size + "（手表 16 / 手环 15 / 耳夹 3，去重后 34 应为 34）");
  eq(idxOf.size, 34, "去重编码总数");
  const bandCodes = BK.find(x => x.key === "band").codes, band11 = BK.find(x => x.key === "band:11").codes;
  eq(band11.every(c => bandCodes.includes(c)), true, "手环11 编码全部含于手环总销量");

  /* ===== 2. 占比分母口径 ===== */
  console.log("\n== 2. 占比分母 = 全平台该品类（含所有服务商与商品卡，仅剔除 IGNORED_ROOMS）==");
  const ref = b.run(`(function(){
    var rows=globalThis.__rows, ix=CODE_IX;
    function calc(codes){
      var o=0,a=0,set=codes?new Set(codes):null;
      rows.forEach(function(r){
        var nick=String(r["达人昵称"]==null?"":r["达人昵称"]).trim();
        if(!nick||isIgnored(nick)) return;
        if(set){
          var cl=String(r["商家编码"]==null?"":r["商家编码"]).replace(/\\t/g,"").split(/[;,；，]/).map(function(s){return s.trim();}).filter(Boolean);
          if(!cl.some(function(c){return set.has(c);})) return;
        }
        o++; a+=parseFloat(String(r["订单应付金额"]).replace(/[,，\\s¥￥元]/g,""))||0;
      });
      return {o:o,a:+a.toFixed(2)};
    }
    var denom={}, per={};
    BLOCKS.forEach(function(bl){ if(bl.level>0) denom[bl.key]=calc(Array.from(bl.codes)); });
    var idx=CODE_IX;
    rows.forEach(function(r){
      var nick=String(r["达人昵称"]==null?"":r["达人昵称"]).trim();
      if(!nick||isIgnored(nick)) return;
      var amt=parseFloat(String(r["订单应付金额"]).replace(/[,，\\s¥￥元]/g,""))||0;
      var cl=String(r["商家编码"]==null?"":r["商家编码"]).replace(/\\t/g,"").split(/[;,；，]/).map(function(s){return s.trim();}).filter(Boolean);
      var hit=new Set();
      cl.forEach(function(c){var a=idx.get(c); if(a) a.forEach(function(k){hit.add(k);});});
      var agent=ROOM_TO_AGENT[nick]||FALLBACK_AGENT;
      hit.forEach(function(k){ per[agent]=per[agent]||{}; per[agent][k]=per[agent][k]||{o:0,a:0}; per[agent][k].o++; per[agent][k].a+=amt; });
    });
    return {denom:denom, per:per};
  })()`);

  // 2.1 分母与页面合计行一致
  const totRow = out[out.length - 1];
  let denomDiff = 0;
  BK.forEach((x, i) => {
    if (x.level === 0) return;
    const d = ref.denom[x.key];
    const pageO = totRow.cells[1 + i * 3], pageA = totRow.cells[2 + i * 3];
    if (pageO !== d.o || Math.abs(pageA - d.a) > 0.011) { denomDiff++; console.log("  X " + x.name + " 合计行 " + pageO + "/" + pageA.toFixed(2) + " vs " + d.o + "/" + d.a.toFixed(2)); }
  });
  eq(denomDiff, 0, "各区块合计行 = 独立复算的分母");

  // 2.2 服务商行 = 复算
  let numDiff = 0, checked = 0;
  BK.forEach((x, i) => {
    if (x.level === 0) return;
    out.filter(r => r.kind === "agent").forEach(r => {
      const agent = r.cells[0];
      const e = (ref.per[agent] || {})[x.key] || { o: 0, a: 0 };
      checked++;
      if (r.cells[1 + i * 3] !== e.o || Math.abs(r.cells[2 + i * 3] - e.a) > 0.011) {
        numDiff++;
        if (numDiff < 5) console.log("  X " + agent + " / " + x.name + " 页面 " + r.cells[1 + i * 3] + "/" + r.cells[2 + i * 3] + " vs " + e.o + "/" + e.a.toFixed(2));
      }
    });
  });
  eq(numDiff, 0, "服务商 × 区块（" + checked + " 组）分子与复算一致");

  // 2.3 占比值 = 分子/分母
  let shareDiff = 0;
  BK.forEach((x, i) => {
    if (x.level === 0) return;
    const D = ref.denom[x.key].a;
    out.filter(r => r.kind === "agent").forEach(r => {
      const amt = r.cells[2 + i * 3], sh = r.cells[3 + i * 3];
      const want = (D > 0 && amt > 0) ? amt / D : null;
      if (want == null) { if (sh !== null) { shareDiff++; console.log("  X " + r.cells[0] + "/" + x.name + " 无金额应为空，实际 " + sh); } }
      else if (Math.abs(sh - want) > 1e-4) { shareDiff++; console.log("  X " + r.cells[0] + "/" + x.name + " 占比 " + sh + " vs " + want.toFixed(6)); }
    });
  });
  eq(shareDiff, 0, "每个服务商 × 区块的占比 = 本行该品类金额 ÷ 全平台该品类金额");

  // 2.4 各区块合计占比 = 100%
  let sumBad = 0;
  BK.forEach((x, i) => {
    if (x.level === 0) return;
    const D = ref.denom[x.key].a;
    if (!D) return;
    let sum = 0;
    out.filter(r => r.kind === "agent").forEach(r => { if (r.cells[3 + i * 3] != null) sum += r.cells[3 + i * 3]; });
    if (Math.abs(sum - 1) > 1e-3) { sumBad++; console.log("  X " + x.name + " 服务商占比之和 = " + (sum * 100).toFixed(3) + "%"); }
  });
  eq(sumBad, 0, "各区块服务商占比之和 = 100%");

  /* ===== 3. 渲染文本与数值一致 ===== */
  console.log("\n== 3. 页面渲染的占比文本 = 数值（1 位小数，四舍五入）==");
  const tb = b.cache.get("#tbody");
  // 桩里 tbody 用 appendChild 收 <tr>，故从 children 取
  const rowsHtml = tb.children.map(el => el.innerHTML);   // 含名称列的 td 已在外层拼接
  // 用 exportData 顺序对齐
  const dataRows = out;                        // 与 tbody 行同序（agent→rooms→total）
  eq(rowsHtml.length, dataRows.length, "tbody 行数 = 数据行数");
  let textBad = 0, textChecked = 0;
  rowsHtml.forEach((h, ri) => {
    const cells = [...h.matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)].map(m => m[1]);
    const pr = dataRows[ri];
    BK.forEach((x, i) => {
      const shareVal = pr.cells[3 + i * 3];
      const html = cells[3 + i * 3] || "";    // 0=名称 1+i*3=销量 2+i*3=金额 3+i*3=占比
      textChecked++;
      const isRoom = pr.kind === "room";
      if (isRoom) {
        if (!/—/.test(html)) { textBad++; if (textBad < 4) console.log("  X 直播间行占比应为 —，实际 " + html); }
      } else if (shareVal == null) {
        if (!/—/.test(html)) { textBad++; if (textBad < 4) console.log("  X 空占比应为 —，实际 " + html); }
      } else {
        const want = (shareVal * 100).toFixed(1) + "%";
        if (!html.includes(want)) { textBad++; if (textBad < 4) console.log("  X " + pr.cells[0] + " " + x.name + " 期望 " + want + " 实际 " + html.replace(/<[^>]+>/g, "")); }
      }
    });
  });
  eq(textBad, 0, "渲染占比文本（共比对 " + textChecked + " 格）");

  /* ===== 4. 边界情况 ===== */
  console.log("\n== 4. 边界 ==");
  const negRows = b.G("window.__exportData") && true;
  // 有单无额（金额 0 但有订单）
  let zeroAmt = 0;
  out.filter(r => r.kind === "agent").forEach(r => {
    BK.forEach((x, i) => {
      if (x.level === 0) return;
      if (r.cells[1 + i * 3] > 0 && r.cells[2 + i * 3] === 0) { zeroAmt++; console.log("  注意：" + r.cells[0] + " / " + x.name + " 有 " + r.cells[1 + i * 3] + " 单但金额为 0，占比显示 —"); }
    });
  });
  ok(zeroAmt === 0, "无「有单无额」导致占比失效的组合");
  // 负金额
  const negs = b.run(`(function(){ var n=0; globalThis.__rows.forEach(function(r){ var v=parseFloat(String(r["订单应付金额"]).replace(/[,，\\s¥￥元]/g,""))||0; if(v<0) n++; }); return n; })()`);
  eq(negs, 0, "无负数金额行（否则占比可能为负）");
  // 占比越界
  let outOfRange = 0;
  BK.forEach((x, i) => {
    if (x.level === 0) return;
    out.filter(r => r.kind === "agent").forEach(r => {
      const sh = r.cells[3 + i * 3];
      if (sh != null && (sh < -1e-9 || sh > 1 + 1e-9)) outOfRange++;
    });
  });
  eq(outOfRange, 0, "所有占比落在 0~100%");

  /* ===== 5. 占比矩阵（人工可读） ===== */
  console.log("\n== 5. 占比矩阵 ==");
  const blocks = BK.filter(x => x.level > 0);
  const head = "服务商".padEnd(10) + blocks.map(x => x.name.slice(-6).padStart(9)).join("");
  console.log(head);
  out.filter(r => r.kind === "agent").forEach(r => {
    let line = String(r.cells[0]).padEnd(10);
    blocks.forEach((x, k) => {
      const i = BK.indexOf(x);
      const sh = r.cells[3 + i * 3];
      line += (sh == null ? "—" : (sh * 100).toFixed(1) + "%").padStart(9);
    });
    console.log(line);
  });
  let lineT = "合计".padEnd(10);
  blocks.forEach((x, k) => {
    const i = BK.indexOf(x);
    const sh = totRow.cells[3 + i * 3];
    lineT += (sh == null ? "—" : (sh * 100).toFixed(1) + "%").padStart(9);
  });
  console.log(lineT);

  console.log("\n结果：通过 " + pass + " 项，失败 " + fail + " 项");
  process.exit(fail ? 1 : 0);
})();
