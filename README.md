# ljg-skill-paper

论文深读器。给它一篇论文，它告诉你：填了什么缺口，增量站不站得住，一个带了二十年研究生的博导怎么评。

## 安装

将此仓库克隆到 Claude Code skills 目录：

```bash
git clone https://github.com/lijigang/ljg-skill-paper.git /tmp/ljg-skill-paper && \
  cp -r /tmp/ljg-skill-paper/skills/ljg-paper ~/.claude/skills/ && \
  rm -rf /tmp/ljg-skill-paper
```

## 使用

```
/ljg-paper https://arxiv.org/abs/2401.xxxxx
/ljg-paper ~/Downloads/some-paper.pdf
/ljg-paper Attention Is All You Need
```

支持 arxiv URL、PDF、本地文件、论文名称搜索。

## 输出

一篇连贯的 Org-mode 分析（Denote 规范），存入 `~/Documents/notes/`。包含：

1. **缺口与增量** — 已有研究的边界在哪，这篇论文往前推了多远
2. **核心机制** — ASCII 结构图 + 承重类比，看完能复述方法逻辑
3. **关键概念** — 1-3 个钥匙概念，费曼技巧从零讲透
4. **餐巾纸速写** — 一张图看清新旧框架的结构位移
5. **博导审稿** — 选题、方法、实验、写作，最后一句判决
6. **启发** — 迁移、混搭、反转：对我有什么用？

## License

MIT
