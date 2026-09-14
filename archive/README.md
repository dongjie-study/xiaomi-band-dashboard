# archive —— 归档区

**这里的脚本已不参与任何日常流程。** 保留是为了「万一要重出报告」，不是为了继续用。

> ⚠️ 与 `tools/` 的区别：`tools/` 里的脚本**仍是活的**（需要时会跑，如月报、周报）；
> `archive/` 里的**已结项或已被取代**。

---

## 一、一次性 / 已结项

| 脚本 | 干什么 | 为什么归档 | 现在还能跑吗 |
|------|--------|-----------|-------------|
| `build_html.py` | 渲染 618 复盘页 | 618 已结项；**import 即执行**（没有 `__main__` 守卫） | ⚠️ 能，但会**覆盖** `节点总结/618复盘总结.html` |
| `generate_618_data.py` | 618 数据抽取 **v1** | 被 `_v2` 取代，两者写同一个 json | ⚠️ 输入 Excel 在桌面，路径已写死 |
| `generate_618_data_v2.py` | 618 数据抽取 **v2** | 618 已结项 | ⚠️ 同上 |
| `generate_report_docx.py` | 618 手表复盘 Word | 输出文件不存在，无任何引用 | ❌ 输出路径写死且指向不存在的目录 |
| `generate_band_improvement_docx.py` | 提升方案呈报 Word | 输出文件不存在，无任何引用 | ⚠️ 需 `python-docx` |
| `generate_anchor_report.py` | 7月主播复盘报告 | **依赖的 `anchor_summary.json` 已不在桌面** | ❌ 一跑就崩 |
| `generate_qianchuan_w5.py` | 千川视频 W5 分析页 | 一次性；输出目录 `核心指标分析/` 不存在 | ❌ 输出目录缺失 |
| `update_product_categories.py` | 商品类目收敛 | 2026-06-26 一次性，已完成 | ⚠️ **会原地改写 `history.json`**，别乱跑 |
| `618_analysis_data.json` | 上面 618 脚本的数据 | 随脚本一起归档 | — |

## 二、明令禁用

| 脚本 | 说明 |
|------|------|
| `update_daily_html.py` | **`WORKFLOW.md` 明确写了「不要运行」**。业绩流程已改为手工维护 `主播业绩/业绩demo.html`，这个脚本会整块改写 `DAILY_RECORDS`，跑一次就可能覆盖当天数据。 |

---

## 三、跑这些脚本要注意

1. **依赖根目录的共享模块**（`team_config.py` / `product_classifier.py` / `formatters.py`）。
   归档时已把各脚本的 `ROOT` / `DATA_DIR` 改成上跳一级（指向项目根），
   `sys.path.insert` 会自动生效，所以**从任何目录调用都能找到模块**。

2. **`build_html.py` 是唯一没有 `__main__` 守卫的**——`import` 它就会执行并写文件。
   它的读写路径已改为相对自身位置（读 `archive/618_analysis_data.json`）
   与相对项目根（写 `节点总结/618复盘总结.html`）。

3. **`generate_618_data*.py` 的输出 `618_analysis_data.json` 写的是 cwd**，
   所以要么 `cd archive` 再跑，要么接受它落在当前目录。

4. **动 `history.json` 的三个脚本**（`update_product_categories.py` 在归档区，
   `sales_analysis/daily_update.py`、`tools/migrate_reclassify.py` 不在）
   ——跑之前先备份，见 `WORKFLOW.md` 的「🚑 修坏数据的标准动作」。

---

## 四、确认可以彻底删除的条件

以下都满足时，整个 `archive/` 可以删：

- 618 / 千川 / 7月主播复盘 都不需要再重出报告
- 确认不再需要 `update_daily_html.py` 的旧逻辑（当前流程已完全脱离它）

删之前建议 `git tag archive-before-delete` 打个标签，随时能找回来。
