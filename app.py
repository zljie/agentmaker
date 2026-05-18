"""
NextStudio - AgentScope + FastHTML
本体驱动 Agent 构建平台

启动: python app.py
访问: http://localhost:5000
"""
import json
from starlette.requests import Request
from starlette.responses import JSONResponse

from fasthtml.common import *
from pathlib import Path

from config import HOST, PORT, DEBUG
from routes.api import api_routes
from routes.pages import page_routes


# 创建 FastHTML 应用
app = FastHTML(
    title="NextStudio",
    debug=DEBUG,
    hdrs=(
        Link(rel="stylesheet", href="/static/css/app.css"),
    ),
)


# 注册路由
api_routes(app)
page_routes(app)


# 静默处理 FastHTML 内部 JSONDecodeError（parse_form 先尝试 json 再降级到 form）
app.add_exception_handler(json.decoder.JSONDecodeError, lambda req, exc: JSONResponse({"error": "Invalid JSON"}, status_code=400))


# 静态文件
@app.route("/static/{path:path}")
async def static_file(req, path: str):
    """静态文件服务"""
    static_dir = Path(__file__).parent / "static"
    file_path = static_dir / path

    if file_path.exists() and file_path.is_file():
        from starlette.responses import FileResponse
        return FileResponse(file_path)

    return {"error": "Not found"}, 404


def main():
    """启动服务器"""
    print(f"""
╔═══════════════════════════════════════════════════════╗
║                                                       ║
║   NextStudio - AgentScope + FastHTML                  ║
║   本体驱动 Agent 构建平台 (Python 版本)                ║
║                                                       ║
║   🌐 http://localhost:{PORT}                          ║
║                                                       ║
║   技术栈:                                             ║
║   - FastHTML (前端框架)                               ║
║   - AgentScope (Agent 运行时)                         ║
║   - Mock Connector (演示用)                           ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
    """)

    import uvicorn
    uvicorn.run(
        "app:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level="info",
    )


if __name__ == "__main__":
    main()
