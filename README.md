# PHUNT

> 🚀 每日自动抓取 Product Hunt 热门产品，生成中文宣传视频

> 🚀 Automatically fetch Product Hunt trending products and generate Chinese promotional videos

---

## 功能特点 / Features

- 🤖 **自动抓取** — 获取 Product Hunt 每日 Top 5 产品
- ✍️ **AI 文案** — 使用 MiMo 模型生成中文口播文案，支持三种风格
- 🎙️ **TTS 语音** — MiMo-V2.5-TTS 语音合成
- 🎯 **Whisper 对齐** — 语音转文字，精确时间戳
- 🎨 **智能配色** — 自动提取产品图片主色调
- 🎬 **视频渲染** — HyperFrames 生成 1080×1920 竖屏视频

---

## 流程 / Pipeline

```
Stage 1: 抓取 Product Hunt Top 5
Stage 2: 选择产品
Stage 2.5: 选择文案风格（口语风/故事风/分析风）
Stage 3: LLM 生成文案 → 手动审核
Stage 4: TTS 语音合成
Stage 5: Whisper 时间对齐
Stage 6: 下载产品图片 + 提取配色
Stage 7: 生成 HyperFrames HTML
Stage 8: 渲染视频
```

---

## 三种文案风格 / 3 Copywriting Styles

| 风格 / Style | 特点 / Description |
|--------------|-------------------|
| **口语风** | 短句、口语化、有梗、直接说好处 |
| **故事风** | 场景代入、描述痛点、产品是解决方案 |
| **分析风** | 深度拆解、数据支撑、专业视角 |

---

## 安装 / Installation

### 1. 克隆仓库 / Clone Repository

```bash
git clone https://github.com/hjss191/phunt.git
cd phunt
```

### 2. 安装依赖 / Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量 / Configure Environment

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥
# Edit .env file and fill in your API keys
```

### 4. 安装 HyperFrames（必须全局安装 / Must install globally）

```bash
npm install -g hyperframes
```

⚠️ **必须使用 `-g` 全局安装**，否则渲染时 `npx` 会提示确认导致卡住。

⚠️ **Must use `-g` for global installation**, otherwise `npx` will prompt for confirmation and block the rendering process.

---

## 使用 / Usage

```bash
python main.py
```

流程会暂停在 Stage 3，等待你审核文案文件。修改完成后按回车继续。

The pipeline pauses at Stage 3 for manual copy review. Edit the file and press Enter to continue.

---

## 项目结构 / Project Structure

```
phunt/
├── main.py              # 主流程 / Main pipeline
├── config.py            # 配置管理 / Configuration
├── phunt_client.py      # Product Hunt API 客户端
├── copywriter.py        # 文案生成 / Copy generation
├── voice_gen.py         # TTS 语音合成
├── aligner.py           # Whisper 时间对齐
├── image_gen.py         # 图片下载 / Image download
├── palette.py           # 配色提取 / Color palette extraction
├── html_gen.py          # HTML 生成 / HTML generation
├── video_gen.py         # 视频渲染 / Video rendering
├── formatter.py         # 输出格式化 / Output formatting
├── srt_parser.py        # SRT 解析 / SRT parsing
├── templates/
│   ├── srt_prompt.txt   # Prompt 模板 / Prompt template
│   ├── styles.json      # 风格配置 / Style configuration
│   └── html_prompt.txt  # HTML 模板 / HTML template
└── output/              # 生成内容（gitignored）
```

---

## 环境变量 / Environment Variables

| 变量 / Variable | 说明 / Description |
|----------------|-------------------|
| `PHUNT_API_TOKEN` | Product Hunt API Token |
| `MIMO_API_KEY` | MiMo API Key |
| `MIMO_BASE_URL` | MiMo API Base URL |
| `MIMO_TTS_API_KEY` | MiMo TTS API Key |
| `MIMO_TTS_BASE_URL` | MiMo TTS API Base URL |

---

## Whisper 模型 / Whisper Model

默认使用 `large-v3-turbo` 模型，需要 GPU 支持。

Default model is `large-v3-turbo`, which requires GPU.

### 无显卡用户 / No GPU Users

如果没有显卡，使用较小的模型：

If you don't have a GPU, use a smaller model:

```python
# 在 aligner.py 中修改 model_name 参数
# Change model_name parameter in aligner.py

# 推荐 / Recommended:
model_name = "base"      # 最快，准确度一般 / Fastest, moderate accuracy
model_name = "small"     # 平衡 / Balanced
model_name = "medium"    # 较准，较慢 / More accurate, slower
```

或在调用时指定 / Or specify when calling:

```python
alignment = align_plain(audio_path, plain_text, model_name="base")
```

| 模型 / Model | 大小 / Size | 速度 / Speed | 准确度 / Accuracy |
|-------------|------------|-------------|------------------|
| `base` | 140MB | ⚡⚡⚡ | ⭐⭐ |
| `small` | 460MB | ⚡⚡ | ⭐⭐⭐ |
| `medium` | 1.5GB | ⚡ | ⭐⭐⭐⭐ |
| `large-v3-turbo` | 3GB | ⚡ | ⭐⭐⭐⭐⭐ |

---

## 依赖 / Dependencies

- Python 3.10+
- openai, requests, python-dotenv, httpx, Pillow, faster-whisper, zhconv
- Node.js（用于 HyperFrames 视频渲染）
- ffmpeg（音视频处理）

---

## License

MIT
