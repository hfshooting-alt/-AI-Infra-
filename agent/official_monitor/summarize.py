from __future__ import annotations

import logging
import os
import re
from typing import List, Tuple

from .models import NormalizedArticle

logger = logging.getLogger(__name__)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _clip_zh(text: str, limit: int) -> str:
    t = _normalize_text(text)
    if len(t) <= limit:
        return t
    window = t[:limit]
    cut = max(window.rfind("。"), window.rfind("！"), window.rfind("？"), window.rfind("；"))
    if cut >= int(limit * 0.6):
        return window[: cut + 1]
    return window.rstrip("，、；：, ")


def _excerpt(text: str, limit: int) -> str:
    t = _normalize_text(text)
    if not t:
        return ""
    sentences = [x.strip() for x in re.split(r"(?<=[。！？!?])", t) if x.strip()]
    if not sentences:
        return _clip_zh(t, limit)
    out = ""
    for s in sentences:
        if len(out) + len(s) > limit:
            break
        out += s
    return out or _clip_zh(sentences[0], limit)


GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEFAULT_MODEL = "gemini-3.0-flash-preview"


def _llm_client():
    api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key, base_url=GEMINI_BASE_URL)
    except Exception:
        return None


def summarize_article_zh(article: NormalizedArticle) -> str:
    base = (article.summary or "").strip()
    core = base or _excerpt(article.content_text, 150) or _clip_zh(article.title, 100)
    signal = "；".join(article.tags[:3]) if article.tags else (article.signal_type or "event")
    entity = article.company_or_firm_name
    out = f"核心内容：{core} 关键信号：{signal}。涉及主体：{entity}。"
    return _clip_zh(out, 260)


def summarize_cluster_event_zh(cluster: List[NormalizedArticle], topic_keywords: List[str]) -> Tuple[str, str]:
    key = "、".join(topic_keywords[:4]) if topic_keywords else "AI产品与投资动态"
    text_pool = " ".join([(a.title + " " + (a.content_text or "")[:500]) for a in cluster[:8]])
    sampled = _excerpt(text_pool, 200)
    inst_cnt = len({(a.company_or_firm_name or '').strip() for a in cluster if (a.company_or_firm_name or '').strip()})
    event_cnt = len(cluster)
    lead = f"过去一周该话题汇总了{event_cnt}起官方事件（涉及{inst_cnt}家机构），主线聚焦“{key}”。"
    summary = lead + (sampled if sampled else '多家机构在产品发布、平台能力与生态合作上同步动作。')
    summary = _clip_zh(summary, 260)

    strategic = "投行视角：关注可量化的产品上线、资金流向与组织变动，噪音事件权重降至最低。"
    if any("融资" in (a.content_text + a.title) for a in cluster):
        strategic = "投资与产业方叙事开始同频，资金与产品路线联动信号增强。"
    if any(k in key for k in ["推理", "reasoning", "多模态"]):
        strategic = "模型竞争正转向推理质量、效率和可用性，而非单纯参数规模。"
    return summary, strategic


def summarize_with_llm(cluster: List[NormalizedArticle], topic_keywords: List[str]) -> Tuple[str, str] | None:
    client = _llm_client()
    if client is None:
        return None
    model = os.environ.get("OFFICIAL_MONITOR_SUMMARY_MODEL", os.environ.get("GEMINI_MODEL", DEFAULT_MODEL))
    bullets = []
    for a in cluster[:8]:
        body = _excerpt(a.content_text, 280)
        bullets.append(f"- 标题：{a.title}\n  机构：{a.company_or_firm_name}\n  内容：{body}")
    prompt = (
        "请基于以下官方文章，输出中文两行：\n"
        "第一行以‘事件总结：’开头（<=220字）；\n"
        "第二行以‘战略信号：’开头（<=80字）。\n"
        "不要使用省略号，不要编造。\n\n"
        f"关键词：{','.join(topic_keywords[:8])}\n" + "\n".join(bullets)
    )
    try:
        resp = client.chat.completions.create(model=model, max_tokens=65536, messages=[{"role": "user", "content": prompt}])
        text = (resp.choices[0].message.content or "") if resp.choices else ""
    except Exception:
        logger.warning("summarize_with_llm failed", exc_info=True)
        return None
    summary, strategic = "", ""
    for ln in [x.strip() for x in text.splitlines() if x.strip()]:
        if ln.startswith("事件总结："):
            summary = ln.split("：", 1)[1].strip()
        elif ln.startswith("战略信号："):
            strategic = ln.split("：", 1)[1].strip()
    if summary:
        return _clip_zh(summary, 260), _clip_zh(strategic or "信号显示平台化与商业化进程持续加速。", 90)
    return None


def summarize_article_with_llm(article: NormalizedArticle) -> Tuple[str, bool] | None:
    """Summarise an article and judge its relevance in a single LLM call.

    Returns ``(summary_text, keep)`` where *keep* is True when the article
    passes the relevance bar, or ``None`` on failure.
    """
    client = _llm_client()
    if client is None:
        return None
    model = os.environ.get("OFFICIAL_MONITOR_SUMMARY_MODEL", os.environ.get("GEMINI_MODEL", DEFAULT_MODEL))
    body = _excerpt(article.content_text, 1200)
    prompt = (
        "你是我们团队的 AI 产业分析师。我们每周从各大 AI 公司和投资机构的官网抓取文章，"
        "你的工作是帮我判断哪些值得放进周报、哪些可以跳过。\n\n"
        "请你读完这篇文章后，按顺序完成三步：\n\n"
        "## 第一步：思考（REASON 行）\n"
        "用一两句话说说你的判断依据。问自己这几个问题：\n"
        "- 这篇文章里有没有具体的、可验证的新信息？"
        "（比如发布了什么、上线了什么、收购了谁、融了多少钱、技术指标是多少）\n"
        "- 如果一个 AI 从业者这周没看到这篇，他会错过什么？\n"
        "- 这篇的信息密度高吗？是言之有物，还是泛泛而谈？\n\n"
        "一些参考（不是硬规则，请结合上下文灵活判断）：\n"
        "  值得收录的典型例子：新模型发布、产品重大更新、深度技术文章（有数据有方法）、"
        "战略合作/收购、融资事件、高管变动、有干货的长播客\n"
        "  通常跳过的典型例子：入门科普教程、纯概念解释、空洞的趋势展望、"
        "营销软文、客户故事、日常运维公告、招聘页面\n"
        "  灰色地带怎么办：如果你犹豫，看信息密度——"
        "同样是客户案例，如果有具体技术架构和性能数据就留，如果只是感言就跳过；"
        "同样是趋势文章，如果有一手数据和独到判断就留，如果是老生常谈就跳过。\n\n"
        "输出格式：REASON: 你的一两句判断依据\n\n"
        "## 第二步：裁决（VERDICT 行）\n"
        "基于你的思考，给出结论：\n"
        "VERDICT: KEEP（收录）或 VERDICT: SKIP（跳过）\n\n"
        "## 第三步：中文摘要（不超过 250 字）\n"
        "格式：核心内容：... 关键信号：... 涉及主体：...\n"
        "如果 SKIP，关键信号写无。不要编造信息。\n\n"
        "---\n"
        f"标题：{article.title}\n机构：{article.company_or_firm_name}\n正文：{body}"
    )
    try:
        resp = client.chat.completions.create(model=model, max_tokens=65536, messages=[{"role": "user", "content": prompt}])
        text = (resp.choices[0].message.content or "") if resp.choices else ""
    except Exception:
        logger.warning("summarize_article_with_llm failed for %s", article.title, exc_info=True)
        return None
    if not text:
        return None

    keep = True
    if "VERDICT: SKIP" in text or "VERDICT:SKIP" in text:
        keep = False

    # Strip REASON/VERDICT meta lines, keep only the summary part
    summary_lines = []
    for ln in text.splitlines():
        stripped = ln.strip()
        if stripped.startswith("REASON:") or stripped.startswith("VERDICT:"):
            continue
        if stripped.startswith("##") or stripped == "---":
            continue
        if stripped:
            summary_lines.append(stripped)
    summary = _normalize_text(" ".join(summary_lines))
    return _clip_zh(summary, 300), keep


def infer_entities(article: NormalizedArticle) -> List[str]:
    txt = article.title + " " + article.content_text[:1200]
    cands = []
    for ent in ["OpenAI", "Anthropic", "Google", "Microsoft", "NVIDIA", "AWS", "Meta", "腾讯", "百度", "红杉", "高瓴", "启明"]:
        if ent.lower() in txt.lower():
            cands.append(ent)
    if not cands:
        cands = [article.company_or_firm_name]
    return cands[:6]



def summarize_cluster_bundle_with_llm(cluster: List[NormalizedArticle], topic_keywords: List[str]) -> Tuple[str, str, str] | None:
    """Use LLM to generate trend-level topic title + intro summary + strategic signal."""
    client = _llm_client()
    if client is None:
        return None
    model = os.environ.get("OFFICIAL_MONITOR_SUMMARY_MODEL", os.environ.get("GEMINI_MODEL", DEFAULT_MODEL))
    bullets = []
    for a in cluster[:10]:
        body = _excerpt(a.article_summary_zh or a.content_text, 220)
        bullets.append(f"- 机构：{a.company_or_firm_name}\n  标题：{a.title}\n  结构化：{body}")
    prompt = (
        "你是投行研究总监，正在为管理层写本周 AI 行业简报。\n"
        "请基于以下事件输出三行中文，要求客观、精炼、对决策有用：\n"
        "第一行：以’话题标题：’开头（<=24字），提炼行业趋势主线，不要写单个公司名称。\n"
        "第二行：以’事件引言：’开头（<=120字），总结本周跨机构的关键动作和事实。\n"
        "第三行：以’战略信号：’开头（<=70字），给出对投资或业务的含义。\n"
        "注意：聚焦实质性事件（发布、上线、收购、融资、人事等），"
        "如果本组事件信息密度不够高，在引言中如实说明。不要编造。\n\n"
        f"关键词：{','.join(topic_keywords[:8])}\n" + "\n".join(bullets)
    )
    try:
        resp = client.chat.completions.create(model=model, max_tokens=65536, messages=[{"role": "user", "content": prompt}])
        text = (resp.choices[0].message.content or "") if resp.choices else ""
    except Exception:
        logger.warning("summarize_cluster_bundle_with_llm failed", exc_info=True)
        return None

    title = intro = signal = ""
    for ln in [x.strip() for x in text.splitlines() if x.strip()]:
        if ln.startswith("话题标题："):
            title = ln.split("：", 1)[1].strip()
        elif ln.startswith("事件引言："):
            intro = ln.split("：", 1)[1].strip()
        elif ln.startswith("战略信号："):
            signal = ln.split("：", 1)[1].strip()
    if title and intro:
        return _clip_zh(title, 30), _clip_zh(intro, 140), _clip_zh(signal or "资本、产品与生态动作正在同步加速。", 90)
    return None
