/* 通用回归：任意订单文件 → 页面聚合 + 导出 + 独立复核
   用法: node v5.js <订单文件路径> */
const fs = require("fs");
const path = require("path");
const { boot } = require("./boot.js");

const ORDERS = process.argv[2] || "C:/Users/Administrator/Desktop/10.27日服务商.xlsx";
const fname = path.basename(ORDERS);

let pass = 0, fail = 0;
const ok = (c, m) => { c ? pass++ : (fail++, console.log("  X " + m)); };
const eq = (a, b, m) => ok(a === b, m + "  期望=" + b + " 实际=" + a);
const near = (a, b, m, eps = 0.02) => ok(Math.abs(a - b) <= eps, m + "  期望=" + b + " 实际=" + a);

(async () => {
  const b = boot();
  const raw = fs.readFileSync(ORDERS);
  b.sb.__raw = raw;

  console.log("文件: " + fname + "  (" + (raw.length / 1024).toFixed(0) + " KB)");

  /* ---- 解析 ---- */
  b.run(`
    var __wb = XLSX.read(new Uint8Array(__raw), {type:"array", cellDates:false});
    globalThis.__sheets = __wb.SheetNames.slice();
    var __sn = pickSheet(__wb);
    globalThis.__sn = __sn;
    var __p = sheetToRows(__wb.Sheets[__sn]);
    globalThis.__rows = __p.rows;
    globalThis.__header = __p.header;
  `);
  const rowsN = b.run("globalThis.__rows.length");
  const sheets = b.run("globalThis.__sheets");
  const header = b.run("globalThis.__header");
  console.log("工作表: " + sheets.join(" / ") + "  选中: " + b.run("globalThis.__sn") + "  数据行: " + rowsN);
  console.log("表头: " + header.join(" | "));

  /* ---- 列识别 ---- */
  const cols = b.run(`(function(){
    var keys = Object.keys(globalThis.__rows[0] || {});
    return {
      amt: pickCol(keys, {exact:["订单应付金额"], prefer:["应付金额"], any:["实付金额","订单金额","支付金额","成交金额","金额"], avoid:["退款","退还","退回","运费","单价","优惠","积分"]}),
      nick: pickCol(keys, {exact:["达人昵称"], prefer:["达人昵称","达人名称"], any:["直播间名称","直播间","主播昵称","账号昵称","昵称"]}),
      time: pickCol(keys, {exact:["提交时间"], prefer:["提交时间","下单时间","支付时间","创建时间"], any:["时间"], avoid:["发货","签收","完成","退款","售后","核销"]}),
      status: pickCol(keys, {exact:["订单状态"], prefer:["订单状态"], any:["状态"], avoid:["退款状态","售后状态"]}),
      code: pickCol(keys, {exact:["商家编码"], prefer:["商家编码","商品编码"], any:["编码","货号"]})
    };
  })()`);
  console.log("识别列: 金额=" + cols.amt + " 昵称=" + cols.nick + " 时间=" + cols.time + " 状态=" + cols.status + " 编码=" + cols.code);
  ["amt", "nick", "time", "status", "code"].forEach(k => ok(!!cols[k], "识别到 " + k + " 列"));

  /* ---- 聚合 ---- */
  const t0 = Date.now();
  b.run(`process(globalThis.__rows, ${JSON.stringify(fname)}, globalThis.__sn);`);
  console.log("聚合耗时: " + (Date.now() - t0) + " ms");
  eq(b.alerts.length, 0, "无 alert（若有会在此列出：" + JSON.stringify(b.alerts) + "）");

  const out = b.G("window.__exportData");
  const BK = b.G("BLOCKS.map(b=>({key:b.key,name:b.name,level:b.level,codes:b.codes?Array.from(b.codes):null}))");
  const TOTAL_COLS = b.G("TOTAL_COLS");
  const tot = out[out.length - 1].cells;
  const blkO = {}, blkA = {};
  BK.forEach((x, i) => { blkO[x.key] = tot[1 + i * 3]; blkA[x.key] = tot[2 + i * 3]; });
  console.log("\n整体: " + blkO.all + " 单  ¥" + blkA.all.toFixed(2));
  BK.forEach((x, i) => {
    if (x.key === "all") return;
    console.log("  " + x.name.padEnd(18) + String(blkO[x.key]).padStart(6) + " 单  ¥" + blkA[x.key].toFixed(2));
  });

  /* ---- 独立复核（同 realm 内重算） ---- */
  const ref = b.run(`(function(){
    var rows = globalThis.__rows;
    var isIgn = isIgnored;
    function calc(codes){
      var o=0,a=0; var set = codes ? new Set(codes) : null;
      rows.forEach(function(r){
        var nick = r[${JSON.stringify(cols.nick)}]==null ? "" : String(r[${JSON.stringify(cols.nick)}]).trim();
        if(!nick || isIgn(nick)) return;
        if(set){
          var cl = String(r[${JSON.stringify(cols.code)}]==null?"":r[${JSON.stringify(cols.code)}]).replace(/\\t/g,"").split(/[;,；，]/).map(function(s){return s.trim();}).filter(Boolean);
          if(!cl.some(function(c){return set.has(c);})) return;
        }
        var v = parseFloat(String(r[${JSON.stringify(cols.amt)}]).replace(/[,，\\s¥￥元]/g,"")) || 0;
        o++; a += v;
      });
      return {o:o, a:a};
    }
    var res = {};
    var blocks = BLOCKS;
    for(var i=0;i<blocks.length;i++){
      var bl = blocks[i];
      res[bl.key] = calc(bl.level===0 ? null : Array.from(bl.codes));
    }
    // 房间级
    var rooms = {};
    rows.forEach(function(r){
      var nick = r[${JSON.stringify(cols.nick)}]==null?"":String(r[${JSON.stringify(cols.nick)}]).trim();
      if(!nick || isIgn(nick)) return;
      rooms[nick] = rooms[nick] || {o:0,a:0};
      rooms[nick].o++; rooms[nick].a += parseFloat(String(r[${JSON.stringify(cols.amt)}]).replace(/[,，\\s¥￥元]/g,"")) || 0;
    });
    // 状态分布
    var st = {};
    rows.forEach(function(r){
      var s = r[${JSON.stringify(cols.status)}]==null?"":String(r[${JSON.stringify(cols.status)}]).trim();
      st[s] = (st[s]||0)+1;
    });
    // 编码分布
    var codes = {};
    rows.forEach(function(r){
      String(r[${JSON.stringify(cols.code)}]==null?"":r[${JSON.stringify(cols.code)}]).replace(/\\t/g,"").split(/[;,；，]/).map(function(s){return s.trim();}).filter(Boolean).forEach(function(c){ codes[c]=(codes[c]||0)+1; });
    });
    return {blk:res, rooms:rooms, status:st, codes:codes};
  })()`);

  // 区块逐项
  let blkDiff = 0;
  BK.forEach(x => {
    const r = ref.blk[x.key];
    if (blkO[x.key] !== r.o || Math.abs(blkA[x.key] - r.a) > 0.011) {
      blkDiff++;
      console.log("  X 【" + x.name + "】页面 " + blkO[x.key] + "/" + blkA[x.key].toFixed(2) + " vs 复核 " + r.o + "/" + r.a.toFixed(2));
    }
  });
  eq(blkDiff, 0, "8 个区块的销量/金额与独立复核全部一致");

  // 房间逐项
  const roomRows = out.filter(x => x.kind === "room");
  let roomDiff = 0;
  roomRows.forEach(x => {
    const nick = String(x.cells[0]).replace(/\u3000/g, "");
    const rf = ref.rooms[nick];
    if (!rf) { roomDiff++; console.log("  X 页面多出房间:" + nick); return; }
    if (x.cells[1] !== rf.o || Math.abs(x.cells[2] - rf.a) > 0.011) { roomDiff++; console.log("  X 房间 " + nick + " 页面 " + x.cells[1] + "/" + x.cells[2] + " vs 复核 " + rf.o + "/" + rf.a.toFixed(2)); }
  });
  eq(roomDiff, 0, "直播间行(" + roomRows.length + " 个)与独立复核全部一致");
  eq(roomRows.length, Object.keys(ref.rooms).length, "直播间个数一致");

  // 模块 = 子项之和
  const s2 = ks => ks.reduce((s, k) => ({ o: s.o + blkO[k], a: s.a + blkA[k] }), { o: 0, a: 0 });
  const wS = s2(["watch:r6", "watch:s5"]), bS = s2(["band:11", "band:10p"]);
  eq(blkO.watch, wS.o, "手表总销量 = 子项订单数之和");
  near(blkA.watch, wS.a, "手表总销量金额 = 子项之和");
  eq(blkO.band, bS.o, "手环总销量 = 子项订单数之和");
  near(blkA.band, bS.a, "手环总销量金额 = 子项之和");

  // 耳夹单独看
  const ec = ref.blk.earclip;
  console.log("\n红米耳夹: " + ec.o + " 单  ¥" + ec.a.toFixed(2));
  ["82612", "82614", "92090"].forEach(c => console.log("    编码 " + c + " 出现 " + (ref.codes[c] || 0) + " 行"));

  /* ---- 占比 ---- */
  let shareBad = 0;
  BK.forEach((x, i) => {
    const whole = blkA[x.key];
    if (x.key === "all" || !whole) return;
    let sum = 0;
    out.filter(r => r.kind === "agent").forEach(r => {
      const amt = r.cells[2 + i * 3], sh = r.cells[3 + i * 3];
      const want = amt > 0 ? amt / whole : null;
      if (want == null) { if (sh !== null) shareBad++; }
      else { if (Math.abs(sh - want) > 1e-4) shareBad++; sum += sh; }
    });
    if (Math.abs(sum - 1) > 1e-3) { shareBad++; console.log("  X 【" + x.name + "】服务商占比之和=" + sum); }
  });
  eq(shareBad, 0, "各区块占比 = 本行/全平台，且服务商占比之和 = 100%");
  eq(roomRows.every(r => { for (let i = 3; i < r.cells.length; i += 3) if (r.cells[i] !== null) return false; return true; }), true, "直播间行不显示占比");

  /* ---- 表头 ---- */
  const thead = b.cache.get("#theadSvc").innerHTML;
  eq((thead.match(/服务商占比/g) || []).length, BK.length, "表头占比列数 = 区块数");
  eq((thead.match(/colspan="3"/g) || []).length, BK.length, "表头分组数 = 区块数");
  ok(thead.includes("红米耳夹"), "表头含 红米耳夹");
  ok(!thead.includes("陶瓷白"), "表头不含 陶瓷白");
  ok(!/<span class="sub-mark">└<\/span> 红米耳夹/.test(thead), "红米耳夹 为一级模块（无 └）");

  /* ---- 警告区 ---- */
  const warn = b.cache.get("#warnBox").innerHTML.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  console.log("\n提示区: " + (warn ? warn.slice(0, 400) : "（无）"));
  ok(!warn.includes("不在映射表内"), "无未映射直播间");
  ok(!warn.includes("无法解析"), "无时间解析失败");

  /* ---- 小时透视 ---- */
  const hg = b.G("window.__hourGroups");
  const hours = b.G("window.__hourHours");
  eq(hg.length, 2, "小时透视两组服务商");
  const names = hg.flatMap(g => g.rooms.map(r => r.nick));
  ok(!names.some(n => n.includes("商品卡")), "小时透视不含商品卡");
  ok(names.includes("小米耳机官旗直播间") || !ref.rooms["小米耳机官旗直播间"], "耳机官旗直播间口径一致");
  console.log("小时范围: " + hours[0] + "~" + hours[hours.length - 1] + "（" + hours.length + " 个时段），直播间 " + names.length + " 个");
  const hgm = hg.reduce((s, g) => s + Object.keys(g.sub).reduce((t, h) => t + g.sub[h].gmv, 0), 0);
  let cur = null, cmp = 0;
  out.forEach(r => {
    if (r.kind === "agent") cur = r.cells[0];
    else if (r.kind === "room" && ["我司阳光", "良米"].includes(cur) && !r.cells[0].includes("商品卡")) cmp += r.cells[2];
  });
  near(hgm, cmp, "小时透视 GMV = 汇总表同口径销售额");
  console.log("  小时GMV " + hgm.toFixed(2) + " / 汇总同口径 " + cmp.toFixed(2));

  /* ---- 状态分布 ---- */
  console.log("\n订单状态分布:");
  Object.keys(ref.status).sort((a, c) => ref.status[c] - ref.status[a]).forEach(s => {
    const n = ref.status[s];
    console.log("  " + (s || "(空)").padEnd(12) + String(n).padStart(6) + " 行" + (b.G("isRefundStatus")(s) ? "  ← 计为退费" : ""));
  });

  /* ---- 导出 ---- */
  b.run(`download = function(buf,name){ globalThis.__o = buf; globalThis.__nm = name; };`);
  await b.G("exportSvc")();
  const obuf = b.run("globalThis.__o");
  ok(!!obuf, "导出缓冲区生成");
  b.sb.__out = obuf;
  const r2 = await b.run(`(function(){
    var wb = new ExcelJS.Workbook();
    return wb.xlsx.load(__out).then(function(){
      var ws = wb.getWorksheet("直播间销售汇总");
      var rows=[];
      ws.eachRow({includeEmpty:true}, function(row,n){
        var v=[]; for(var c=1;c<=ws.columnCount;c++) v.push(row.getCell(c).value);
        rows.push(v);
      });
      return {rowCount:ws.rowCount, colCount:ws.columnCount, data:rows.slice(2, rows.length-1), note:rows[rows.length-1][0],
              fmt:[ws.getRow(3).getCell(2).numFmt, ws.getRow(3).getCell(3).numFmt, ws.getRow(3).getCell(4).numFmt]};
    });
  })()`);
  eq(r2.colCount, TOTAL_COLS, "导出列数 = TOTAL_COLS");
  eq(r2.data.length, out.filter(x => x.kind !== "header").length, "导出行数 = 页面行数");
  let cellDiff = 0, cellCmp = 0;
  out.filter(x => x.kind !== "header").forEach((pr, i) => {
    const xl = r2.data[i]; if (!xl) { cellDiff++; return; }
    for (let c = 0; c < TOTAL_COLS; c++) {
      const a = pr.cells[c], bb = xl[c]; cellCmp++;
      const aN = a === null || a === undefined || a === "", bN = bb === null || bb === undefined || bb === "";
      if (aN && bN) continue;
      if (aN !== bN) { cellDiff++; continue; }
      if (typeof a === "number") { if (Math.abs(a - bb) > 1e-6) cellDiff++; }
      else if (String(a).replace(/\u3000/g, "") !== String(bb).replace(/\u3000/g, "")) cellDiff++;
    }
  });
  eq(cellDiff, 0, "导出逐格比对（" + cellCmp + " 格）");
  console.log("导出: " + r2.rowCount + " 行 × " + r2.colCount + " 列，逐格比对 " + cellCmp + " 格，差异 " + cellDiff);
  eq(r2.fmt[0] + "|" + r2.fmt[1] + "|" + r2.fmt[2], "#,##0|#,##0.00|0.0%", "数字格式");
  ok(String(r2.note).includes("红米耳夹属耳机品类"), "底注含耳夹说明");

  /* ---- 落盘 ---- */
  const outPath = "C:/Users/Administrator/Desktop/小米手环直播间销量分析/校验_" + fname.replace(/\.xlsx$/i, "") + "_导出结果.xlsx";
  try { fs.writeFileSync(outPath, Buffer.from(obuf)); console.log("已写出: " + outPath); }
  catch (e) {
    const alt = outPath.replace(/\.xlsx$/i, "_最新.xlsx");
    fs.writeFileSync(alt, Buffer.from(obuf));
    console.log("原文件被占用（可能正被 Excel 打开），已改写到: " + alt);
  }

  console.log("\n结果：通过 " + pass + " 项，失败 " + fail + " 项");
  process.exit(fail ? 1 : 0);
})();
