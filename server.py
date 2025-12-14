# server.py
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv
import os
import uuid

from database import get_db
from models import ChatMessage
from sqlalchemy.orm import Session
from llm_client import get_llm_client

# 加载 .env 文件中的配置
load_dotenv()

# 检查环境变量
print("=== 环境变量检查 ===")
print(f"LLM_PROVIDER 的值是：{os.getenv('LLM_PROVIDER')}")
api_key = os.getenv('DEEPSEEK_API_KEY', '未找到')
if api_key != '未找到':
    print(f"DEEPSEEK_API_KEY 的前几位是：{api_key[:10]}...")
else:
    print("DEEPSEEK_API_KEY: 未找到")
print("==================")

# 创建 FastAPI 应用
app = FastAPI(title="AI桌面机器人服务器")

# 允许网页跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建必要的目录
os.makedirs("templates", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("static/img", exist_ok=True)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 设置模板
templates = Jinja2Templates(directory="templates")


# 数据模型
class ChatRequest(BaseModel):
    message: str
    user_id: str = "default_user"
    session_id: str = None


# 路由
@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """主页 - 返回新的现代化界面"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/test", response_class=HTMLResponse)
async def test_page():
    """旧版测试页面"""
    with open("test.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/status")
async def api_status():
    """API 状态检查"""
    return {
        "status": "running",
        "service": "AI Desktop Robot",
        "version": "1.0.0"
    }


@app.post("/api/chat")
async def chat_api(
        request: ChatRequest,
        db: Session = Depends(get_db)
):
    """聊天 API 接口"""
    # 优先使用 session_id，如果没有则使用 user_id
    session_id = request.session_id or request.user_id

    # 如果是第一次对话，生成一个新的 session_id
    if session_id == "default_user" or session_id == "test":
        session_id = str(uuid.uuid4())
        print(f"[Session] 生成新会话ID: {session_id}")

    # 定义要保留的对话轮数
    MAX_HISTORY_TURNS = 3
    query_limit = MAX_HISTORY_TURNS * 2

    # 查询最近的对话消息（按时间正序排列）
    history_messages = db.query(ChatMessage) \
        .filter(ChatMessage.session_id == session_id) \
        .order_by(ChatMessage.created_at.asc()) \
        .limit(query_limit) \
        .all()

    # 构建消息列表
    messages_for_ai = []

    # 如果是第一次对话，添加一个简单的系统提示
    if len(history_messages) == 0:
        messages_for_ai.append({
            "role": "system",
            "content": "你是一个友好的AI助手，请直接回答用户的问题，保持对话自然流畅。"
        })

    # 添加历史消息
    messages_for_ai.extend([
        {"role": msg.role, "content": msg.content}
        for msg in history_messages
    ])

    # 添加当前用户消息
    messages_for_ai.append({"role": "user", "content": request.message})

    print(f"[Context] 会话ID: {session_id}, 准备 {len(messages_for_ai)} 条上下文消息。")

    # 保存用户消息到数据库
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=request.message
    )
    db.add(user_msg)
    db.commit()

    # 4. 调用AI获取回复
    print(f"[LLM] 调用AI，消息数量: {len(messages_for_ai)}")
    print(f"[LLM] 最后一条用户消息: {request.message}")

    client = get_llm_client()
    ai_reply = await client.chat(messages_for_ai)

    print(f"[LLM] AI回复长度: {len(ai_reply)} 字符")
    print(f"[LLM] AI回复前200字符: {ai_reply[:200]}")

    # 保存AI回复
    ai_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=ai_reply
    )
    db.add(ai_msg)
    db.commit()

    return {
        "reply": ai_reply,
        "session_id": session_id,
        "history_length": len(history_messages) + 2,
        "status": "success",
        "reply_length": len(ai_reply)  # 添加回复长度便于调试
    }


@app.get("/api/sessions")
async def get_sessions(db: Session = Depends(get_db)):
    """获取所有会话列表"""
    sessions = db.query(
        ChatMessage.session_id,
        ChatMessage.content,
        ChatMessage.created_at
    ).order_by(ChatMessage.created_at.desc()).all()

    # 按会话ID分组
    session_dict = {}
    for session_id, content, created_at in sessions:
        if session_id not in session_dict:
            session_dict[session_id] = {
                "session_id": session_id,
                "last_message": content[:50] + "..." if len(content) > 50 else content,
                "last_activity": created_at.isoformat(),
                "message_count": 0
            }
        session_dict[session_id]["message_count"] += 1

    return {"sessions": list(session_dict.values())}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str, db: Session = Depends(get_db)):
    """删除指定会话"""
    deleted_count = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).delete()
    db.commit()

    return {
        "status": "success",
        "deleted_count": deleted_count,
        "message": f"已删除会话 {session_id} 的 {deleted_count} 条消息"
    }


@app.get("/api/sessions/{session_id}/messages")
async def get_session_messages(
        session_id: str,
        db: Session = Depends(get_db),
        limit: int = 100
):
    """获取特定会话的所有消息"""
    try:
        print(f"[API] 获取会话消息: {session_id}")

        # 查询该会话的所有消息，按时间正序排列
        messages = db.query(ChatMessage) \
            .filter(ChatMessage.session_id == session_id) \
            .order_by(ChatMessage.created_at.asc()) \
            .limit(limit) \
            .all()

        print(f"[API] 找到 {len(messages)} 条消息")

        # 格式化消息
        formatted_messages = []
        for msg in messages:
            formatted_msg = {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "session_id": msg.session_id
            }

            # 处理时间戳
            if hasattr(msg, 'created_at') and msg.created_at:
                formatted_msg["created_at"] = msg.created_at.isoformat()
            else:
                formatted_msg["created_at"] = None

            formatted_messages.append(formatted_msg)

        return {
            "session_id": session_id,
            "messages": formatted_messages,
            "count": len(formatted_messages),
            "status": "success"
        }

    except Exception as e:
        print(f"[API] 错误: {str(e)}")
        return {
            "session_id": session_id,
            "error": str(e),
            "status": "error"
        }


@app.get("/api/sessions/{session_id}/summary")
async def get_session_summary(
        session_id: str,
        db: Session = Depends(get_db)
):
    """获取会话摘要信息"""
    try:
        # 获取会话中的消息数量
        total_messages = db.query(ChatMessage) \
            .filter(ChatMessage.session_id == session_id) \
            .count()

        # 获取第一条和最后一条消息的时间
        first_message = db.query(ChatMessage) \
            .filter(ChatMessage.session_id == session_id) \
            .order_by(ChatMessage.created_at.asc()) \
            .first()

        last_message = db.query(ChatMessage) \
            .filter(ChatMessage.session_id == session_id) \
            .order_by(ChatMessage.created_at.desc()) \
            .first()

        # 获取第一条用户消息作为会话标题
        first_user_message = db.query(ChatMessage) \
            .filter(
            ChatMessage.session_id == session_id,
            ChatMessage.role == "user"
        ) \
            .order_by(ChatMessage.created_at.asc()) \
            .first()

        summary = {
            "session_id": session_id,
            "total_messages": total_messages,
            "created_at": first_message.created_at.isoformat() if first_message else None,
            "last_activity": last_message.created_at.isoformat() if last_message else None,
            "title": first_user_message.content[:50] + "..." if first_user_message and len(
                first_user_message.content) > 50 else (first_user_message.content if first_user_message else "新会话")
        }

        return {
            "session_id": session_id,
            "summary": summary,
            "status": "success"
        }

    except Exception as e:
        return {
            "session_id": session_id,
            "error": str(e),
            "status": "error"
        }

if __name__ == "__main__":
    print("🚀 启动 AI 桌面机器人服务器...")
    print("📁 主页: http://localhost:8000/")
    print("📄 旧版测试: http://localhost:8000/test")
    print("📚 API文档: http://localhost:8000/docs")

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )