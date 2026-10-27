/* 同 realm 沙箱：在 vm 上下文内加载 xlsx / exceljs UMD，避免跨 realm 的 instanceof 失效
   导出：/exportSvc 与真实浏览器行为一致 */
const fs = require("fs");
const vm = require("vm");

const path = require("path");
// 相对本文件定位，换机器/换目录不用改（脚本在 校验脚本/，页面在仓库根目录）
const HTML = path.resolve(__dirname, "..", "直播间销量汇总工具.html");
const XLSX_SRC = "node_modules/xlsx/dist/xlsx.full.min.js";
const EXCELJS_SRC = "node_modules/exceljs/dist/exceljs.min.js";

function mkDom() {
  const mk = tag => {
    const el = { tagName: tag, children: [], _html: "", textContent: "", value: "", className: "", dataset: {}, style: {},
      classList: { _s: new Set(), add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); }, toggle() {}, contains(c) { return this._s.has(c); } },
      addEventListener() {}, removeEventListener() {}, appendChild(c) { this.children.push(c); return c; },
      setAttribute() {}, getAttribute() { return null; }, remove() {}, focus() {}, click() {},
      querySelector() { return mk("div"); }, querySelectorAll() { return []; } };
    Object.defineProperty(el, "innerHTML", { get() { return this._html; }, set(v) { this._html = v; } });
    return el;
  };
  const cache = new Map();
  return {
    cache,
    document: {
      querySelector(s) { if (!cache.has(s)) cache.set(s, mk("div")); return cache.get(s); },
      querySelectorAll() { return []; },
      createElement(t) { return mk(t); },
      addEventListener() {}, body: mk("body"), documentElement: mk("html"), head: mk("head"), write() {}
    }
  };
}

function boot() {
  const html = fs.readFileSync(HTML, "utf8");
  const scripts = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]);
  const pageCode = scripts.find(s => s.includes("ROOM_TO_AGENT"));

  const { document, cache } = mkDom();
  const alerts = [];
  const sb = { console, setTimeout, clearTimeout, setInterval, clearInterval,
    alert: m => alerts.push(m), document, navigator: { userAgent: "node" }, location: { href: "file:///x.html" },
    FileReader: function () {}, URL: { createObjectURL: () => "blob:x", revokeObjectURL() {} }, Blob: function () {},
    addEventListener() {}, removeEventListener() {} };
  // 先建上下文（获得独立 realm 的标准内置对象），再注入宿主对象
  vm.createContext(sb);
  sb.window = sb;
  sb.self = sb;
  sb.globalThis = sb;

  // 在上下文内加载第三方库 → 与页面代码同 realm
  vm.runInContext(fs.readFileSync(XLSX_SRC, "utf8"), sb, { filename: "xlsx.full.min.js" });
  vm.runInContext(fs.readFileSync(EXCELJS_SRC, "utf8"), sb, { filename: "exceljs.min.js" });
  sb.XLSX = vm.runInContext("XLSX", sb);
  sb.ExcelJS = vm.runInContext("ExcelJS", sb);

  vm.runInContext(pageCode, sb, { filename: "page.js" });
  return { sb, alerts, cache,
    G: n => vm.runInContext(n, sb),
    run: c => vm.runInContext(c, sb),
    eval: code => vm.runInContext(code, sb) };
}

module.exports = { boot };
