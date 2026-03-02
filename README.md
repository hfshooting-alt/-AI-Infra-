# ljg-skill-paper

论文深读器 — 一个 Claude Code Skill，用原子管线解构学术论文，输出连贯的认知旅程。

## 功能

- **原子管线**：Split(拆结构) → Squeeze(榨增量) → Plain(白话方法/核喻) → Feynman(关键概念费曼讲解) → Napkin Sketch(餐巾纸速写) → 博导审稿
- **多来源支持**：arxiv URL、PDF 文件、本地 markdown/org 文件、论文名称搜索
- **输出格式**：Denote 规范的 Org-mode 文件，存入 `~/Documents/notes/`
- **核心关注**：这篇论文填了什么缺口？增量站不站得住？一个带了二十年研究生的博导怎么评？

## 安装

```bash
/plugin marketplace add lijigang/ljg-skill-paper
/plugin install ljg-paper
```

## 使用

```
/ljg-paper https://arxiv.org/abs/2401.xxxxx
/ljg-paper 读论文 [附带 PDF 路径]
/ljg-paper Attention Is All You Need
```

## 认知路径

```
论文 = 一个增量
  |
  v
拆结构(split): 缺口、假设、方法、证据、贡献声明
  |
  v
榨增量(squeeze): before vs after，世界多了什么？+ 核心机制 ASCII 图
  |
  v
白话方法(plain): 为核心机制找承重的结构类比（核喻）
  |
  v
费曼概念(feynman): 1-3 个关键概念从零讲透
  |
  v
餐巾纸速写(napkin sketch): 一张图看清新旧框架的结构位移
  |
  v
博导审稿: 选题眼光、方法成熟度、实验诚意、写作功力、一句话判决
  |
  v
综合输出: 编织成一篇连贯分析
```

## 输出质量标准

- **缺口要准**：用自己的话说清研究边界和缺口
- **增量要锐**：一句话说出 before vs after
- **机制要可视**：ASCII 图画出方法内部结构
- **核喻要承重**：去掉它读者就回到看图发呆
- **概念要费曼**：讲完读者能用自己的话复述
- **速写要一眼**：不看正文也能理解位移方向
- **博导要像博导**：白话点评，有判断力有分寸感
- **零割裂感**：像一个人在跟你讲「我读了篇论文」

## License

MIT