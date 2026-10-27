/* 导出验证（同 realm）：真实订单 → exportSvc → 读回校验 */
const fs = require("fs");
const { boot } = require("./boot.js");

const ORDERS = "C:/Users/Administrator/Desktop/订单文件夹/10.26日订单.xlsx";

let pass = 0, fail = 0;
const ok = (c, m) => { c ? pass++ : (fail++, console.log("  X " + m)); };
const eq = (a, b, m) => ok(a === b, m + "  期望=" + b + " 实际=" + a);
const near = (a, b, m, eps = 1e-6) => ok(Math.abs(a - b) <= eps, m + "  期望=" + b + " 实际=" + a);

(async () => {
  const { G, run, alerts } = boot();
  eq(alerts.length, 0, "加载无 alert");

  console.log("== ① 合成数据：耳夹三个编码 ==");
  const rows = [
    { 选购商品: "红米耳夹A", 商家编码: "82612", 订单提交时间: "2026-10-26 10:00:00", 订单状态: "已完成", 订单应付金额: 199, 达人昵称: "小米耳机官旗直播间" },
    { 选购商品: "红米耳夹B", 商家编码: "82614", 订单提交时间: "2026-10-26 11:00:00", 订单状态: "已完成", 订单应付金额: 299, 达人昵称: "小米耳机官旗直播间" },
    { 选购商品: "红米耳夹C", 商家编码: "92090", 订单提交时间: "2026-10-26 12:00:00", 订单状态: "已完成", 订单应付金额: 399, 达人昵称: "小米手表" },
    { 选购商品: "耳夹+手环", 商家编码: "82612;81244", 订单提交时间: "2026-10-26 13:00:00", 订单状态: "已完成", 订单应付金额: 500, 达人昵称: "小米手环11直播间" },
    { 选购商品: "手环", 商家编码: "81244", 订单提交时间: "2026-10-26 14:00:00", 订单状态: "已关闭", 订单应付金额: 249, 达人昵称: "小米手环11直播间" },
    { 选购商品: "手表", 商家编码: "68698", 订单提交时间: "2026-10-26 15:00:00", 订单状态: "已完成", 订单应付金额: 599, 达人昵称: "小米耳机官旗直播间" }
  ];
  G("process")(rows, "synthetic.xlsx", "Sheet1");
  const out = G("window.__exportData");
  const BK = G("BLOCKS.map(b=>b.key)");
  const tot = out[out.length - 1].cells;
  const v = k => { const i = BK.indexOf(k); return { o: tot[1 + i * 3], a: tot[2 + i * 3], s: tot[3 + i * 3] }; };
  eq(v("earclip").o, 4, "耳夹订单数=4（含 1 条组合编码）");
  eq(v("earclip").a, 1397, "耳夹销售额=199+299+399+500");
  eq(v("band").o, 2, "手环订单数=2");
  eq(v("band").a, 749, "手环销售额=500+249");
  eq(v("watch").o, 1, "手表订单数=1");
  eq(v("all").o, 6, "整体订单数=6（已关闭也计单）");
  eq(v("all").a, 2245, "整体销售额=199+299+399+500+249+599");
  near(v("earclip").s, 1, "合计行耳夹占比=100%");
  const liang = out.find(r => r.kind === "agent" && r.cells[0] === "良米");
  ok(!!liang, "良米行存在");
  if (liang) {
    const ei = BK.indexOf("earclip");
    eq(liang.cells[1 + ei * 3], 4, "良米耳夹 4 单");
    near(liang.cells[2 + ei * 3], 1397, "良米耳夹销售额");
    near(liang.cells[3 + ei * 3], 1, "良米耳夹占比 100%");
  }
  const hg = G("window.__hourGroups").flatMap(g => g.rooms.map(r => r.nick));
  ok(hg.includes("小米耳机官旗直播间"), "小时透视含耳机官旗直播间");

  console.log("\n== ② 真实订单导出 ==");
  const b2 = boot();
  const wb = b2.G("XLSX").readFile
    ? b2.G("XLSX")
    : null;
  // 用上下文内的 XLSX 读文件（同 realm，避免跨 realm 数组）
  b2.run(`globalThis.__raw = null;`);
  const bufIn = fs.readFileSync(ORDERS);
  b2.run(`globalThis.__bufIn = null;`);
  b2.sb.__bufIn = bufIn;
  b2.run(`
    var wbIn = XLSX.read(new Uint8Array(__bufIn), {type:"array", cellDates:false});
    var snIn = pickSheet(wbIn);
    var parsedIn = sheetToRows(wbIn.Sheets[snIn]);
    globalThis.__sn = snIn; globalThis.__n = parsedIn.rows.length;
    process(parsedIn.rows, "10.26日订单.xlsx", snIn);
  `);
  console.log("    工作表:" + b2.run("globalThis.__sn") + " 行数:" + b2.run("globalThis.__n"));
  eq(b2.alerts.length, 0, "真实订单无 alert");

  b2.run(`download = function(buf,name){ globalThis.__out = buf; globalThis.__name = name; };`);
  await b2.G("exportSvc")();
  const outBuf = b2.run("globalThis.__out");
  ok(!!outBuf, "导出缓冲区已生成");
  eq(b2.run("globalThis.__name"), "直播间销售汇总.xlsx", "文件名");

  b2.sb.__outBuf = outBuf;
  const res = b2.run(`(function(){
    var wb = new ExcelJS.Workbook();
    return wb.xlsx.load(__outBuf).then(function(){
      var ws = wb.getWorksheet("直播间销售汇总");
      var rows = [];
      ws.eachRow({includeEmpty:true}, function(row, n){
        var vals = [];
        for(var c=1;c<=ws.columnCount;c++){ vals.push(row.getCell(c).value); }
        rows.push({n:n, vals:vals});
      });
      var noteRow = rows[rows.length-1];
      return {
        rowCount: ws.rowCount,
        colCount: ws.columnCount,
        merges: (ws.model.merges||[]).slice(),
        views: JSON.stringify(ws.views),
        h1: rows[0].vals, h2: rows[1].vals,
        data: rows.slice(2, rows.length-1),
        note: noteRow.vals[0],
        fmtSample: [ws.getRow(3).getCell(2).numFmt, ws.getRow(3).getCell(3).numFmt, ws.getRow(3).getCell(4).numFmt]
      };
    });
  })()`);
  const r = await res;

  console.log("    行数:" + r.rowCount + " 列数:" + r.colCount);
  const BLOCKS = b2.G("BLOCKS.map(b=>b.name)");
  const TOTAL_COLS = b2.G("TOTAL_COLS");
  eq(r.colCount, TOTAL_COLS, "列数 = TOTAL_COLS");
  eq(r.h1[0], "服务商 / 直播间", "A1");
  eq(r.h1[1], "整体", "第1组表头");
  BLOCKS.forEach((n, i) => {
    const start = 1 + i * 3;
    const sub = ["Redmi watch 6", "Watch 系列高端表", "小米手环11", "小米手环10Pro"].includes(n);
    eq(r.h1[start], (sub ? "└ " : "") + n, "第" + (i + 1) + "组表头 = " + n);
    eq(r.h2[start], "销量", n + " 销量列");
    eq(r.h2[start + 1], "销售额(元)", n + " 金额列");
    eq(r.h2[start + 2], "服务商占比", n + " 占比列");
  });
  console.log("    表头1: " + [0, 1, 4, 7, 10, 13, 16, 19, 22].map(i => r.h1[i]).join(" | "));

  // 合并单元格：A1:A2 + 每组 + 底注行
  const m = r.merges;
  ok(m.includes("A1:A2"), "A1:A2 合并");
  eq(m.filter(x => /^[A-Z]+1:[A-Z]+1$/.test(x)).length, BLOCKS.length, "第1行分组合并块数 = 区块数");
  eq(m.length, BLOCKS.length + 2, "合并总数 = 表头 + 各组 + 底注");
  ok(r.views.includes('"ySplit":2') && r.views.includes('"xSplit":1') && r.views.includes('"state":"frozen"'), "冻结前两行 + 首列");

  // 数据行 = 页面 exportData（逐格比对）
  const pageRows = b2.G("window.__exportData").filter(x => x.kind !== "header");
  eq(r.data.length, pageRows.length, "数据行数 = 页面行数");
  let cellDiff = 0, cellCmp = 0;
  pageRows.forEach((pr, i) => {
    const xl = r.data[i];
    if (!xl) { cellDiff++; return; }
    eq0: for (let c = 0; c < TOTAL_COLS; c++) {
      const a = pr.cells[c], bb = xl.vals[c];
      cellCmp++;
      const aNull = a === null || a === undefined || a === "";
      const bNull = bb === null || bb === undefined || bb === "";
      if (aNull && bNull) continue;
      if (aNull !== bNull) { cellDiff++; if (cellDiff < 4) console.log("    差异 r" + (i + 3) + " c" + (c + 1) + " 页面=" + JSON.stringify(a) + " 导出=" + JSON.stringify(bb)); continue; }
      if (typeof a === "number") { if (Math.abs(a - bb) > 1e-6) { cellDiff++; if (cellDiff < 4) console.log("    数值差异 r" + (i + 3) + " c" + (c + 1) + " " + a + " vs " + bb); } }
      else if (String(a).replace(/\u3000/g, "") !== String(bb).replace(/\u3000/g, "")) { cellDiff++; if (cellDiff < 4) console.log("    文本差异 r" + (i + 3) + " c" + (c + 1) + " " + JSON.stringify(a) + " vs " + JSON.stringify(bb)); }
    }
  });
  eq(cellDiff, 0, "逐格比对差异数（共比对 " + cellCmp + " 格）");
  console.log("    逐格比对:" + cellCmp + " 格，差异 " + cellDiff);

  // 合计行
  const totalIdx = pageRows.length - 1;
  const xlTotal = r.data[totalIdx].vals;
  eq(xlTotal[0], "全平台合计", "合计行标签");
  eq(xlTotal[1], pageRows[totalIdx].cells[1], "合计行整体销量");
  near(xlTotal[3], 1, "合计行整体占比=100%");
  near(xlTotal[TOTAL_COLS - 1] === null ? 1 : xlTotal[TOTAL_COLS - 1], 1, "最后一组(红米耳夹)合计占比");

  // 数字格式
  eq(r.fmtSample[0], "#,##0", "销量列格式");
  eq(r.fmtSample[1], "#,##0.00", "金额列格式");
  eq(r.fmtSample[2], "0.0%", "占比列格式");

  // 底注
  ok(String(r.note).includes("服务商占比"), "底注含占比口径");
  ok(String(r.note).includes("红米耳夹属耳机品类"), "底注含耳夹说明");
  ok(!String(r.note).includes("陶瓷白"), "底注不含陶瓷白");

  console.log("\n结果：通过 " + pass + " 项，失败 " + fail + " 项");
  process.exit(fail ? 1 : 0);
})();
