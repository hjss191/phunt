# Product Hunt 每日精选 → 视频生成设计文档

> **目标：** 在现有文案+配音流程基础上，新增视频生成能力。LLM 生成 SRT 格式文案，SRT 同时驱动 TTS 音频和 HyperFrames HTML 画面，最终渲染成 MP4 视频。

---

## 整体流程

```
Step 1: PH 拉取
phunt_client.py → 产品信息 + 截图 URLs

Step 2: 文案生成（SRT 格式）
copywriter.py → LLM 输出 SRT 格式文案
每句话带时间戳（基于中文语速 ~4.5 字/秒估算）
输出：{style}_copy.srt + {style}_copy.txt

Step 3: TTS 配音
voice_gen.py → 从 SRT 提取纯文本 → MiMo TTS → .mp3

Step 4: HTML 生成
html_gen.py → LLM 读 SRT + 产品信息 + 图片
→ 生成 HyperFrames HTML（每句话一个 section，时间绑定）

Step 5: 视频渲染
HyperFrames CLI → HTML + 音频 → MP4
```

---

## SRT 格式设计

LLM 生成文案时，直接输出标准 SRT 格式：

```srt
1
00:00:00,000 --> 00:00:03,200
今天发现一个超厉害的AI工具

2
00:00:03,200 --> 00:00:07,500
它能帮你自动写文案做视频

3
00:00:07,500 --> 00:00:11,800
只需要输入一个产品链接就能搞定
```

### 时间戳估算规则

- 中文语速：~4.5 字/秒
- 每句话字数 ÷ 4.5 = 该句时长
- 句间停顿：0.3-0.5 秒

### 输出文件

- `{style}_copy.srt` — SRT 字幕文件（时间轴 + 文本）
- `{style}_copy.txt` — 纯文本（给 TTS 用，从 SRT 提取）

### Prompt 设计要点

让 LLM 输出 SRT 格式，同时要求：
1. 每句话控制在 10-20 字（适合画面展示）
2. 按 SRT 标准格式输出
3. 时间戳基于中文语速估算

---

## HyperFrames HTML 生成

LLM 读取 SRT + 产品信息 + 图片，生成一个完整的 HTML 文件。

### 核心结构

```html
<div id="stage" data-composition-id="product-video"
     data-start="0" data-width="1080" data-height="1920">

  <!-- 第1句话的画面 -->
  <section class="frame" data-start="0" data-duration="3.2" data-track-index="0">
    <h1>今天发现一个超厉害的AI工具</h1>
    <img src="product_screenshot.png" />
  </section>

  <!-- 第2句话的画面 -->
  <section class="frame" data-start="3.2" data-duration="4.3" data-track-index="0">
    <h2>它能帮你自动写文案做视频</h2>
    <div class="feature-list">...</div>
  </section>

  <!-- 音频轨道 -->
  <audio data-start="0" data-duration="11.8" data-track-index="1" src="audio.mp3"></audio>

  <!-- MVP: 简单 CSS 渐变动画，后续可升级为 GSAP -->
  <style>
    .frame { opacity: 0; animation: fadeIn 0.5s forwards; }
    @keyframes fadeIn { to { opacity: 1; } }
  </style>
</div>
```

### LLM 的任务

1. 读 SRT 的每句话和时间戳
2. 为每句话设计对应的画面（标题、产品截图、特性列表等）
3. 用 `data-start` / `data-duration` 绑定 SRT 时间戳
4. 穿插产品图片
5. 添加 GSAP 入场动画

### 图片处理

PH 拉下来的图片 URL 需要下载到本地，HTML 中引用本地路径。

---

## 视频渲染

### 渲染步骤

1. HyperFrames CLI 读取 HTML 文件
2. headless Chrome 逐帧渲染
3. FFmpeg 编码 + 混合音频
4. 输出 MP4

### 依赖

- Node.js 22+（HyperFrames 需要）
- FFmpeg（HyperFrames 需要）
- `npx hyperframes` CLI

---

## 项目结构

```
phunt/
├── config.py           # 现有
├── phunt_client.py     # 现有
├── copywriter.py       # 改造：输出 SRT 格式
├── voice_gen.py        # 现有（从 SRT 提取文本）
├── image_gen.py        # 现有（下载产品图片）
├── html_gen.py         # 新增：LLM 生成 HyperFrames HTML
├── video_gen.py        # 新增：调用 HyperFrames CLI 渲染
├── formatter.py        # 改造：管理新目录结构
├── main.py             # 改造：加入新步骤
├── templates/
│   └── styles.json     # 现有
└── output/
    └── 2026-06-08/
        ├── copy/       # .srt + .txt
        ├── audio/      # .mp3
        ├── images/     # 产品截图
        ├── html/       # HyperFrames HTML
        └── video/      # 最终 MP4
```

---

## MVP 范围

- 先做 1 种风格（口语风）
- 简单画面（标题 + 产品截图 + 字幕）
- 不做复杂动画
- 竖屏 1080×1920（适配抖音/小红书）

---

## 关键模块说明

### copywriter.py（改造）

- 输入：产品信息
- 输出：SRT 格式文案 + 纯文本
- Prompt 要求 LLM 按 SRT 格式输出，每句话 10-20 字

### html_gen.py（新增）

- 输入：SRT 文件 + 产品信息 + 图片路径
- 输出：HyperFrames HTML 文件
- LLM 读 SRT 时间戳，为每句话设计画面

### video_gen.py（新增）

- 输入：HTML 文件 + 音频文件
- 输出：MP4 视频
- 调用 `npx hyperframes render`

---

## 技术风险

1. **时间戳精度**：估算的时间戳可能和 TTS 实际语速不完全匹配，MVP 阶段可接受
2. **HyperFrames 依赖**：需要 Node.js 22+ 和 FFmpeg，安装可能有门槛
3. **LLM 输出格式**：LLM 可能不严格按 SRT 格式输出，需要解析和容错

### 容错设计

- **HyperFrames 未安装**：检测 `npx hyperframes` 是否可用，不可用时提示用户安装，但仍生成 HTML 文件供手动渲染
- **SRT 解析失败**：如果 LLM 输出不符合 SRT 格式，尝试正则提取时间戳和文本，失败则回退到纯文本模式
- **图片下载失败**：HTML 中使用占位图，不影响视频生成
