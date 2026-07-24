"""
千川直播截图智能分析 - 趋势图诊断
=====================================
用法:
  1. 把千川后台趋势截图放到 screenshots/ 文件夹
  2. 设置环境变量: set ANTHROPIC_API_KEY=sk-ant-xxx
  3. 运行: python analyze_screenshots.py
  4. 结果写入 analysis_result.json，打开 index.html 自动加载

依赖: pip install anthropic pillow
"""

import base64
import json
import os
import sys
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

import anthropic

ROOT = Path(__file__).resolve().parent
SCREENSHOTS_DIR = ROOT / "screenshots"
OUTPUT_FILE = ROOT / "analysis_result.json"
HISTORY_FILE = ROOT / "analysis_history.json"

# ─── 分析提示词 ───────────────────────────────────────────────

SYSTEM_PROMPT = """你是一位资深的抖音千川直播间数据分析师，专门分析小米手环/手表直播间的趋势截图。

你会看到千川后台的直播趋势曲线截图，上面显示了一条或多条指标的实时波动曲线（如平均停留时长、曝光率、浅层互动率、产品点击率等），以及行业参考线（绿色虚线）。

请你仔细观察截图中的每一条曲线，包括但不限于：
- 曲线整体走势（上升/下降/震荡）
- 波峰和波谷的位置
- 和绿色行业参考线的差距
- 曲线的波动幅度
- 开场阶段（左侧） vs 尾段（右侧）的变化
- 是否有断崖式下跌或突然拉升
- 多条曲线之间的关联性（比如某条掉的时候另一条也掉）

然后按以下 JSON 格式输出分析结果（严格返回 JSON，不要其他文字）：

{
  "overview": {
    "health": "good|mid|bad",
    "summary": "一句话总结这场直播的整体表现",
    "score": 72
  },
  "metrics": [
    {
      "name": "指标名称（如：平均停留时长）",
      "value": "估计的均值数字（如 42）",
      "unit": "秒|%|元",
      "target": "行业参考值",
      "level": "good|mid|low",
      "trend": "波动下滑|前低后高|中段断崖|稳中有升|低位震荡|峰值短暂|后段掉量|高点离散",
      "curve_analysis": "曲线具体表现：如开场承接偏慢、18:35左右出现断崖、尾段有回升等",
      "issue": "这条曲线的核心问题是什么",
      "reasons": "导致问题的可能原因（结合主播话术、节奏、商品承接等）",
      "fix": "具体解决办法",
      "action": "下场直播的具体执行动作"
    }
  ],
  "suggestions": {
    "host": ["主播下场要改的 2-3 个动作"],
    "ops": ["运营协同要做的 2-3 个动作"],
    "meeting": ["复盘会重点讨论的 2-3 个问题"]
  },
  "timeline_notes": [
    {
      "time": "大约的时间点",
      "event": "该时间点发生的情况",
      "severity": "critical|warning|info"
    }
  ]
}

重要规则：
1. 如果截图中有多条曲线，每条都作为一个独立的 metric 输出
2. 数值尽量准确估计，标注"(估计)"字样
3. 如果看不清某个具体数字，用范围表示，如 "约40-45"
4. 时间点参考曲线横轴的时间轴来估计
5. 行业参考线通常是一条绿色虚线，把它作为 target
6. 答案必须只包含 JSON，不要有 ```json``` 标记或其他解释文字"""

USER_PROMPT = """请仔细分析这张千川直播趋势截图，识别其中的所有趋势曲线、行业参考线和异常变化点。

对照小米手环/手表直播间的行业基准（平均停留时长 55 秒、曝光率 8%、浅层互动率 6%、产品点击率 22%），
给出针对性的诊断和改进建议。

注意：
- 趋势线是灰色/浅色区域的折线
- 绿色虚线通常是行业参考线
- 横轴是时间（通常是 18:00-20:00 左右）
- 如果截图只展示了一条或两条曲线，就只分析图中能看到的"""

# ─── 分析函数 ─────────────────────────────────────────────────

@dataclass
class AnalysisResult:
    overview: dict = field(default_factory=dict)
    metrics: list = field(default_factory=list)
    suggestions: dict = field(default_factory=dict)
    timeline_notes: list = field(default_factory=list)
    analyzed_at: str = ""
    image_count: int = 0
    image_names: list = field(default_factory=list)


def get_api_key() -> str:
    """获取 API Key: 先从环境变量，再尝试 claude CLI 配置"""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key

    # 尝试从 Claude Code 配置读取
    config_paths = [
        Path.home() / ".claude" / "credentials.json",
        Path.home() / ".anthropic" / "credentials.json",
        Path.home() / ".config" / "anthropic" / "credentials.json",
    ]
    for cfg in config_paths:
        if cfg.exists():
            try:
                data = json.loads(cfg.read_text())
                for k in ("ANTHROPIC_API_KEY", "api_key", "apiKey", "key"):
                    if data.get(k):
                        return data[k]
            except Exception:
                pass
    return ""


def find_images(directory: Path) -> list[Path]:
    """获取截图目录中所有图片文件"""
    extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
    images = []
    for ext in extensions:
        images.extend(directory.glob(f"*{ext}"))
        images.extend(directory.glob(f"*{ext.upper()}"))
    return sorted(images)


def encode_image(path: Path) -> tuple[str, str]:
    """将图片编码为 base64，返回 (media_type, base64_data)"""
    ext = path.suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
    }
    media_type = mime_map.get(ext, "image/png")
    data = base64.b64encode(path.read_bytes()).decode("utf-8")
    return media_type, data


def build_message_content(images: list[Path]) -> list[dict]:
    """构建 Claude 消息内容（文本 + 多张图片）"""
    content = [{"type": "text", "text": USER_PROMPT}]
    for img_path in images:
        mime, b64 = encode_image(img_path)
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": mime,
                "data": b64,
            },
        })
    return content


def parse_response(text: str, images: list[Path]) -> AnalysisResult:
    """解析 Claude 返回的 JSON"""
    # 清理可能的 markdown 包裹
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # 去掉第一行和最后一行 ```
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # 尝试找到 JSON 块
        import re
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                data = {"raw": text, "error": "JSON 解析失败，请查看 raw 字段"}
        else:
            data = {"raw": text, "error": "JSON 解析失败，请查看 raw 字段"}

    return AnalysisResult(
        overview=data.get("overview", {}),
        metrics=data.get("metrics", []),
        suggestions=data.get("suggestions", {}),
        timeline_notes=data.get("timeline_notes", []),
        analyzed_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        image_count=len(images),
        image_names=[img.name for img in images],
    )


def analyze(api_key: str, images: list[Path], model: str = "claude-sonnet-4-20250514") -> AnalysisResult:
    """调用 Claude API 分析截图"""
    client = anthropic.Anthropic(api_key=api_key)

    print(f"📊 正在分析 {len(images)} 张截图...")
    for img in images:
        print(f"   📷 {img.name} ({img.stat().st_size / 1024:.0f} KB)")

    # 压缩大图
    image_objects = []
    for img_path in images:
        mime, b64 = encode_image(img_path)
        image_objects.append({
            "type": "image",
            "source": {"type": "base64", "media_type": mime, "data": b64},
        })

    # 如果图片太多，分批处理
    MAX_IMAGES_PER_REQUEST = 5
    if len(image_objects) <= MAX_IMAGES_PER_REQUEST:
        all_content = [{"type": "text", "text": USER_PROMPT}] + image_objects
        return _call_claude(client, all_content, images, model)
    else:
        # 多批分析，合并结果
        all_metrics = []
        all_timeline = []
        best_overview = {}
        batch_count = (len(image_objects) + MAX_IMAGES_PER_REQUEST - 1) // MAX_IMAGES_PER_REQUEST
        for i in range(0, len(image_objects), MAX_IMAGES_PER_REQUEST):
            batch = image_objects[i:i + MAX_IMAGES_PER_REQUEST]
            batch_num = i // MAX_IMAGES_PER_REQUEST + 1
            print(f"\n--- 第 {batch_num}/{batch_count} 批 ---")
            batch_prompt = f"这是第 {batch_num}/{batch_count} 批截图。{USER_PROMPT}\n\n注意：本批只包含部分截图，请只分析这些图片中能看到的曲线。"
            content = [{"type": "text", "text": batch_prompt}] + batch
            result = _call_claude(client, content, images[i:i + MAX_IMAGES_PER_REQUEST], model)
            all_metrics.extend(result.metrics)
            all_timeline.extend(result.timeline_notes)
            if result.overview:
                best_overview = result.overview

        # 合并去重
        seen_names = set()
        unique_metrics = []
        for m in all_metrics:
            key = m.get("name", "")
            if key not in seen_names:
                seen_names.add(key)
                unique_metrics.append(m)

        return AnalysisResult(
            overview=best_overview,
            metrics=unique_metrics,
            suggestions=result.suggestions,
            timeline_notes=all_timeline,
            analyzed_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            image_count=len(images),
            image_names=[img.name for img in images],
        )


def _call_claude(
    client: anthropic.Anthropic,
    content: list[dict],
    images: list[Path],
    model: str,
) -> AnalysisResult:
    """单次调用 Claude"""
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
        temperature=0.4,
    )

    # 提取文本
    text = ""
    for block in message.content:
        if block.type == "text":
            text += block.text

    print(f"\n✅ 分析完成 (tokens: 输入 {message.usage.input_tokens}, 输出 {message.usage.output_tokens})")
    return parse_response(text, images)


def save_history(result: AnalysisResult):
    """追加到历史记录"""
    history = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            history = []
    history.append(asdict(result))
    # 只保留最近 20 条
    history = history[-20:]
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


# ─── CLI ──────────────────────────────────────────────────────

def main():
    api_key = get_api_key()
    if not api_key:
        print("❌ 未找到 ANTHROPIC_API_KEY")
        print()
        print("请先设置 API Key，任选一种方式：")
        print("  1. 命令行:  set ANTHROPIC_API_KEY=sk-ant-api03-xxx")
        print("  2. 永久:    setx ANTHROPIC_API_KEY sk-ant-api03-xxx")
        print()
        print("获取 Key: https://console.anthropic.com/")
        sys.exit(1)

    images = find_images(SCREENSHOTS_DIR)
    if not images:
        print(f"❌ 在 {SCREENSHOTS_DIR} 中没有找到图片文件")
        print()
        print("请把千川后台趋势截图放到这个文件夹，然后重新运行。")
        print("支持的格式: png / jpg / jpeg / webp / bmp")
        sys.exit(1)

    # 模型选择
    model = os.environ.get("ANALYSIS_MODEL", "claude-sonnet-4-20250514")

    try:
        result = analyze(api_key, images, model)
    except anthropic.AuthenticationError:
        print("❌ API Key 无效，请检查 ANTHROPIC_API_KEY 是否正确")
        sys.exit(1)
    except anthropic.RateLimitError:
        print("❌ API 额度不足或频率超限，请稍后重试")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 分析出错: {e}")
        sys.exit(1)

    # 保存结果
    data = asdict(result)
    OUTPUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    save_history(result)

    print(f"\n📁 分析结果已保存: {OUTPUT_FILE}")
    print(f"📁 历史记录: {HISTORY_FILE}")

    # 摘要打印
    print("\n" + "=" * 60)
    print("📋 分析摘要")
    print("=" * 60)
    health = result.overview.get("health", "mid")
    emoji = {"good": "🟢", "mid": "🟡", "bad": "🔴"}.get(health, "⚪")
    print(f"  整体判断: {emoji} {result.overview.get('summary', '待查看')}")
    print(f"  分析指标数: {len(result.metrics)}")
    print(f"  时间节点: {len(result.timeline_notes)} 个")

    for m in result.metrics:
        level_emoji = {"good": "✅", "mid": "⚠️", "low": "🔴"}.get(m.get("level", ""), "")
        print(f"  {level_emoji} {m.get('name', '?')}: {m.get('issue', '')[:60]}...")

    suggestions = result.suggestions
    if suggestions:
        print(f"\n  🎤 主播动作: {len(suggestions.get('host', []))} 条")
        print(f"  ⚙️ 运营动作: {len(suggestions.get('ops', []))} 条")
        print(f"  📝 会议重点: {len(suggestions.get('meeting', []))} 条")

    print(f"\n💡 打开 index.html 查看完整分析报告（页面会自动加载分析结果）")


if __name__ == "__main__":
    main()
