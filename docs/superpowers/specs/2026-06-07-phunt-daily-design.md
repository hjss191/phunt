# Product Hunt 每日精选 → 多平台发布

## 概述
每天从 Product Hunt 拉取 Top 5 新产品，用户选择一个，AI 生成三种风格的文案（口语风/故事风/分析风），每个风格适配三个平台（抖音/小红书/公众号），同时生成配音音频和赛博风配图，用户手动发布。

## 技术栈

| 环节 | 方案 | 成本 |
|------|------|------|
| 数据源 | Product Hunt GraphQL API | 免费 |
| 文案生成 | MiMo API（OpenAI 兼容） | 按量计费 |
| 配音 | MiMo TTS API | 按量计费 |
| 配图 | 通义万相 API | 有免费额度 |
| 语言 | Python 3.10+ | - |

## 项目结构

```
D:\phunt\
├── main.py              # 主入口：流程调度
├── phunt_client.py      # Product Hunt GraphQL API 客户端
├── copywriter.py        # MiMo 文案生成（3风格 × 3平台）
├── voice_gen.py         # MiMo TTS 配音生成
├── image_gen.py         # 通义万相赛博风配图
├── formatter.py         # 平台格式化 + 文件输出
├── config.py            # 配置管理（API Keys、路径）
├── .env                 # API Keys（gitignore）
├── .env.example         # 配置模板
├── requirements.txt     # 依赖清单
├── templates/
│   └── styles.json      # 三种风格的 prompt 模板
└── output/
    └── YYYY-MM-DD/
        ├── douyin/
        │   ├── style_a_口语风.md
        │   ├── style_b_故事风.md
        │   └── style_c_分析风.md
        ├── xiaohongshu/
        │   ├── style_a_口语风.md
        │   ├── style_b_故事风.md
        │   └── style_c_分析风.md
        ├── wechat/
        │   ├── style_a_口语风.md
        │   ├── style_b_故事风.md
        │   └── style_c_分析风.md
        ├── audio/
        │   ├── douyin_style_a.mp3
        │   ├── xiaohongshu_style_b.mp3
        │   └── ...（最多 9 个）
        └── images/
            ├── cover.png
            └── detail.png
```

## 数据流

```
1. phunt_client.py → Product Hunt GraphQL API → Top 5 产品列表
2. 终端展示列表，用户输入编号选择 1 个产品
3. copywriter.py → MiMo API → 生成 9 份文案（3风格 × 3平台）
4. voice_gen.py → MiMo TTS API → 生成配音 mp3
5. image_gen.py → 通义万相 API → 生成赛博风配图
6. formatter.py → 输出到 output/YYYY-MM-DD/
7. 用户打开文件夹，手动发布到各平台
```

## 模块设计

### phunt_client.py
- 使用 GraphQL 查询 Product Hunt API
- 查询当天 Top 产品（按 votesCount 排序）
- 返回字段：name, tagline, description, url, votesCount, thumbnail, topics
- 默认取 Top 5

### copywriter.py
- 读取 templates/styles.json 中的风格模板
- 对每个风格 × 每个平台组合，调用 MiMo API
- 输入：产品信息 + 风格 prompt + 平台要求
- 输出：文案文本
- 风格模板：
  - **口语风 (style_a)**：短句、口语化、有梗、直接说好处
  - **故事风 (style_b)**：场景代入、描述痛点、产品是解决方案
  - **分析风 (style_c)**：深度拆解、数据支撑、专业视角
- 平台适配：
  - **抖音**：150字以内，口语化，带话题标签
  - **小红书**：300字以内，emoji丰富，种草感，带标签
  - **公众号**：800-1500字，结构化，图文排版

### voice_gen.py
- 调用 MiMo TTS API
- 输入：文案文本
- 输出：mp3 音频文件
- 每个平台选一个最佳风格版本生成配音（初期可先生成全部9个）

### image_gen.py
- 调用通义万相 API
- 根据产品信息自动生成 prompt：赛博朋克/未来科技风格的产品概念图
- 输出：cover.png（封面图）、detail.png（细节图）

### formatter.py
- 创建 output/YYYY-MM-DD/ 目录结构
- 按平台和风格命名文件
- 管理文件写入

### config.py
- 从 .env 读取：
  - `PHUNT_API_TOKEN` — Product Hunt API Token
  - `MIMO_API_KEY` — MiMo API Key
  - `MIMO_BASE_URL` — MiMo API 地址
  - `TONGYI_API_KEY` — 通义万相 API Key
- 管理输出目录路径

## 运行方式

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 API Keys
cp .env.example .env
# 编辑 .env 填入你的 API Keys

# 运行
python main.py
```

交互流程：
1. 脚本启动，拉取 Product Hunt Top 5
2. 终端展示产品列表（名称、简介、票数）
3. 用户输入编号选择产品
4. 脚本依次生成文案、配音、配图
5. 输出完成，提示用户去 output 目录发布

## 依赖

```
openai          # MiMo API 调用（OpenAI 兼容）
requests        # HTTP 请求
python-dotenv   # 环境变量管理
httpx           # 通义万相 API 调用
```

## 后续扩展
- 定时自动运行（Windows 任务计划）
- 桌面通知提醒
- 剪贴板自动复制
- 更多风格模板
- 多产品选择
