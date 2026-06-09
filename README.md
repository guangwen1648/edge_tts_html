# edge_tts_html

基于 [edge-tts](https://github.com/rany2/edge-tts) 的本地 TTS 试听 / 生成 Web 工具，前端 HTML + 后端 Python HTTP 服务。

支持 **322 种微软 Edge 神经语音**（142 种语言），含完整中文（普通话 / 粤语 / 台湾腔）、英、日、韩等。

**🆓 完全免费 · 零账号 · 无需 GPU · 任意电脑可跑**（只需能联网访问微软 TTS 服务）

## 功能

- 🎙️ 322 个音色在线试听、列表浏览、按语言 / 性别筛选
- ✍️ 自定义文本 → 语音合成（MP3 下载）
- 🎚️ 语速 (rate) / 音调 (pitch) / 音量 (volume) 实时调节
- 💾 一键保存到本地 `generated/` 目录（带时间戳命名）
- 🀄 中文 12 语音 + 英文 17 语音 + 日韩 + …

## 目录结构

```
edge-tts-serve/
├── edge-tts-preview.html    # 前端单页应用（104KB，所有音色内置）
├── edge-tts-serve.py        # 后端 Python HTTP 服务（端口 8765）
├── 启动生成服务.ps1              # Windows 一键启动脚本
├── edge-tts-samples/
│   ├── all/                 # 322 个音色示例 MP3（按需试听）
│   └── all-voices.json      # 音色元数据（短名/语言/性别/描述）
├── generated/               # 用户保存的生成结果（已 gitignore）
└── .gitignore
```

## 快速开始

### 0. 硬件要求

- ✅ **CPU / 集显即可** —— 无需独立 GPU、不依赖本地模型
- ✅ **任意电脑** —— 笔记本、台式机、迷你主机都行；老电脑也能跑
- ✅ **内存建议 1GB+**（主要给浏览器和 Python 进程）
- ✅ **操作系统**：Windows / macOS / Linux 均可
- ✅ **网络**：能访问 `https://speech.platform.bing.com/`（edge-tts 后端调用微软云端 TTS，本地不做语音合成计算）

合成全部在微软云端完成，本地只是一个 HTTP 服务 + 浏览器前端，所以对硬件几乎零要求。

### 1. 准备环境

需要 Python 3.9+：

```bash
pip install edge-tts
```

### 2. 启动后端

双击 `启动生成服务.ps1`，或在 PowerShell 里：

```powershell
.\启动生成服务.ps1
```

服务会监听 `http://127.0.0.1:8765`。

### 3. 打开前端

浏览器打开 `edge-tts-preview.html`（建议 Chrome / Edge），点击「加载音色」即可试听。

## API 简表

| 路径 | 方法 | 用途 |
|------|------|------|
| `/voices` | GET | 返回完整音色列表 JSON |
| `/tts` | POST (JSON) | 合成语音，body: `{text, voice, rate, pitch, volume, save}`，返回 MP3 字节流或保存路径 |
| `/health` | GET | 健康检查 |

## 使用示例

### 命令行

```python
import asyncio, edge_tts

async def main():
    await edge_tts.Communicate(
        text="你好，这是测试语音",
        voice="zh-CN-XiaoxiaoNeural",
        rate="-10%",
        pitch="+10Hz"
    ).save("output.mp3")

asyncio.run(main())
```

### Web UI

1. 选音色（在 322 个音色里搜索 / 筛选）
2. 输入文本（建议 ≤ 1000 字）
3. 调语速 / 音调 / 音量
4. 点「试听」直接播放；点「保存到本地」写入 `generated/`

## 常用音色

| ShortName | 说明 |
|-----------|------|
| `zh-CN-XiaoxiaoNeural` | 晓晓（通用女声） |
| `zh-CN-YunxiNeural` | 云希（男声） |
| `zh-CN-YunyangNeural` | 云扬（新闻腔） |
| `zh-CN-YunxiaNeural` | 云夏（活泼女声） |
| `zh-HK-HiuGaaiNeural` | 香港粤语女声 |
| `zh-TW-HsiaoChenNeural` | 台湾女声 |
| `en-US-AvaNeural` | Ava（英文女声） |
| `en-US-AndrewNeural` | Andrew（英文男声） |
| `ja-JP-NanamiNeural` | 日语女声 |
| `ko-KR-SunHiNeural` | 韩语女声 |

## 故障排除

- **中文乱码**：确保 HTML 用 UTF-8 打开
- **合成失败 / 卡顿**：检查是否能访问 `https://speech.platform.bing.com/`
- **找不到语音**：删 `edge-tts-samples/all-voices.json` 后重启服务，会自动重拉
- **端口被占用**：改 `edge-tts-serve.py` 里的 `PORT = 8765`

## License

MIT
