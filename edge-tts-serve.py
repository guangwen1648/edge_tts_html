"""Edge TTS 本地生成服务 - 纯标准库，无需第三方依赖
启动：python edge-tts-serve.py [port]
默认端口 8765
"""
import asyncio
import json
import re
import sys
import tempfile
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

import edge_tts

# MP3 保存目录（脚本所在目录的 generated/ 子目录）
SAVE_DIR = Path(__file__).parent / "generated"


def synthesize(voice: str, text: str, rate: str, pitch: str, volume: str) -> bytes:
    """同步包装异步 edge_tts"""
    async def _run():
        comm = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            pitch=pitch,
            volume=volume,
        )
        chunks = []
        async for c in comm.stream():
            if c["type"] == "audio":
                chunks.append(c["data"])
        return b"".join(chunks)
    return asyncio.run(_run())


def save_mp3(voice: str, text: str, mp3_bytes: bytes,
             rate: int = 0, pitch: int = 0, volume: int = 0) -> Path:
    """保存到 generated/，文件名规则：
    - 默认参数（rate=0, pitch=0, volume=0）: {voice}_{文案前10字}_{时间戳}.mp3
    - 有调整: 在末尾追加 _r{rate}_p{pitch}_v{volume}（仅非默认项）
    文件名示例：
      zh-CN-XiaoxiaoNeural_你好世界这是一段测试_20260608_220000.mp3
      zh-CN-XiaoxiaoNeural_你好世界这是一段_20260608_220000_r-10_p+5.mp3
    """
    SAVE_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_voice = re.sub(r"[^\w\-]", "_", voice)
    snippet = text.strip()[:10]
    safe_snippet = re.sub(r"[^\w一-鿿]", "", snippet) or "audio"

    # 仅当参数 ≠ 0 时加后缀
    extras = []
    if rate != 0:
        extras.append(f"r{rate:+d}")
    if pitch != 0:
        extras.append(f"p{pitch:+d}")
    if volume != 0:
        extras.append(f"v{volume:+d}")
    parts = [safe_voice, safe_snippet, ts] + extras

    fname = "_".join(parts) + ".mp3"
    path = SAVE_DIR / fname
    # 避免 Windows 文件名过长
    if len(str(path)) > 200:
        safe_snippet = safe_snippet[:5]
        parts = [safe_voice, safe_snippet, ts] + extras
        path = SAVE_DIR / ("_".join(parts) + ".mp3")
    path.write_bytes(mp3_bytes)
    return path


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # 简化日志
        sys.stderr.write(f"[{self.log_date_time_string()}] {args[0]}\n")

    def do_OPTIONS(self):
        # CORS 预检
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if urlparse(self.path).path == "/health":
            self._json({"ok": True, "service": "edge-tts-serve"})
        else:
            self._json({"error": "GET /health 或 POST /tts"}, status=404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/tts":
            self._handle_tts()
        else:
            self._json({"error": f"unknown path: {path}"}, status=404)

    def _handle_tts(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            req = json.loads(body.decode("utf-8"))
        except Exception as e:
            return self._json({"error": f"bad request: {e}"}, status=400)

        voice = req.get("voice", "").strip()
        text = req.get("text", "").strip()
        if not voice or not text:
            return self._json({"error": "voice and text are required"}, status=400)

        rate = str(req.get("rate", "0"))
        pitch = str(req.get("pitch", "0"))
        volume = str(req.get("volume", "0"))

        # 转 edge-tts 格式（自动加 +/- 号，避免 ++5Hz 错误）
        def fmt(val, unit):
            val = str(val).strip()
            if val and not val.startswith(("+", "-")):
                val = "+" + val
            return f"{val}{unit}"
        rate_str = fmt(rate, "%")
        pitch_str = fmt(pitch, "Hz")
        volume_str = fmt(volume, "%")

        try:
            mp3_bytes = synthesize(voice, text, rate_str, pitch_str, volume_str)
        except Exception as e:
            return self._json({"error": f"synthesize failed: {e}"}, status=500)

        # 可选：保存到 generated/
        saved_path = None
        if req.get("save"):
            try:
                rate_int = int(rate) if rate.lstrip("-").isdigit() else 0
                pitch_int = int(pitch) if pitch.lstrip("-").isdigit() else 0
                volume_int = int(volume) if volume.lstrip("-").isdigit() else 0
                saved_path = save_mp3(voice, text, mp3_bytes,
                                      rate_int, pitch_int, volume_int)
            except Exception as e:
                sys.stderr.write(f"  [!] save failed: {e}\n")

        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Length", str(len(mp3_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        # 不带 Content-Disposition，浏览器 fetch 后可用 blob URL 播放
        # 也不强制 attachment，避免触发下载
        if saved_path:
            # HTTP header 只支持 latin-1，路径含中文需转 ASCII 安全值
            # 用 base64 编码完整路径，前端可还原
            import base64
            path_b64 = base64.b64encode(str(saved_path).encode("utf-8")).decode("ascii")
            self.send_header("X-Saved-Path-B64", path_b64)
            # 也返回 ASCII 文件名（仅 basename）方便前端显示
            self.send_header("X-Saved-Name", saved_path.name.encode("ascii", "replace").decode("ascii"))
        self.end_headers()
        self.wfile.write(mp3_bytes)
        sys.stderr.write(
            f"  -> {voice} {len(mp3_bytes)/1024:.1f}KB rate={rate_str}"
            f"{' [saved: ' + saved_path.name + ']' if saved_path else ''}\n"
        )

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"Edge TTS 服务已启动: http://127.0.0.1:{port}")
    print(f"  健康检查: GET  http://127.0.0.1:{port}/health")
    print(f"  生成接口: POST http://127.0.0.1:{port}/tts")
    print(f"  请求体: {{\"voice\":\"zh-CN-XiaoxiaoNeural\",\"text\":\"你好\",\"rate\":\"0\",\"pitch\":\"0\",\"volume\":\"0\"}}")
    print(f"  按 Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n停止服务")
        server.server_close()


if __name__ == "__main__":
    main()
