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
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, func
from database import get_db,SessionLocal, engine
from models import ChatMessage
from sqlalchemy.orm import Session
from llm_client import get_llm_client
from database import init_db
init_db()

from typing import List, Optional
from fastapi import Query, HTTPException, status



# 加载 .env 文件中的配置
load_dotenv()

# 在启动时初始化数据库
def init_database():
    """初始化数据库表"""
    from database import init_db
    init_db()
    print("✅ 数据库表已初始化")

# 检查环境变量
print("=== 环境变量检查 ===")
print(f"LLM_PROVIDER 的值是：{os.getenv('LLM_PROVIDER')}")
api_key = os.getenv('MIMO_API_KEY', '未找到')
if api_key != '未找到':
    print(f"MIMO_API_KEY 的前几位是：{api_key[:10]}...")
else:
    print("MIMO_API_KEY: 未找到")
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

class BatchDeleteRequest(BaseModel):
    session_ids: Optional[List[str]] = None
    confirm_password: Optional[str] = None
    keep_latest: Optional[int] = 0  # 保留最近N个会话



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
async def get_sessions(
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(20, ge=1, le=100, description="每页数量"),
        sort_by: str = Query("last_activity", description="排序字段: last_activity, message_count"),
        order: str = Query("desc", description="排序方向: asc, desc"),
        db: Session = Depends(get_db)
):
    """获取分页会话列表"""
    try:
        # 计算分页
        offset = (page - 1) * page_size

        # 获取会话统计
        from sqlalchemy import func

        query = db.query(
            ChatMessage.session_id,
            func.max(ChatMessage.created_at).label('last_activity'),
            func.count(ChatMessage.id).label('message_count'),
            func.max(ChatMessage.content).label('last_message_preview')
        ).group_by(ChatMessage.session_id)

        # 排序
        if sort_by == "last_activity":
            order_by_field = func.max(ChatMessage.created_at)
        elif sort_by == "message_count":
            order_by_field = func.count(ChatMessage.id)
        else:
            order_by_field = func.max(ChatMessage.created_at)

        if order.lower() == "desc":
            query = query.order_by(order_by_field.desc())
        else:
            query = query.order_by(order_by_field.asc())

        # 分页
        total_sessions = query.count()
        sessions = query.offset(offset).limit(page_size).all()

        # 格式化结果
        formatted_sessions = []
        for session in sessions:
            session_id, last_activity, message_count, last_message = session
            formatted_sessions.append({
                "session_id": session_id,
                "last_activity": last_activity.isoformat() if last_activity else None,
                "message_count": message_count,
                "last_message": (last_message[:100] + "...") if last_message and len(last_message) > 100 else (
                            last_message or ""),
                "created_date": last_activity.date().isoformat() if last_activity else None
            })

        return {
            "status": "success",
            "page": page,
            "page_size": page_size,
            "total_sessions": total_sessions,
            "total_pages": (total_sessions + page_size - 1) // page_size,
            "sessions": formatted_sessions,
            "sort": {"by": sort_by, "order": order}
        }

    except Exception as e:
        print(f"[会话列表] 错误: {e}")
        return {
            "status": "error",
            "error": str(e),
            "sessions": []
        }

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


@app.delete("/api/sessions")
async def delete_sessions(
        action: str = Query("all", description="操作类型: all-全部, selected-选择, old-旧会话"),
        keep_latest: int = Query(0, description="保留最近N个会话"),
        confirm: str = Query(None, description="确认密码"),
        db: Session = Depends(get_db)
):
    """
    删除会话 - 多功能接口
    支持多种删除模式：
    1. 删除全部会话
    2. 保留最近N个会话
    3. 按条件删除（预留）
    """
    try:
        # 安全检查
        if confirm != "CONFIRM_DELETE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="需要确认密码 'CONFIRM_DELETE' 才能执行删除操作"
            )

        total_before = db.query(ChatMessage).count()

        if action == "all":
            # 删除所有会话
            deleted_count = db.query(ChatMessage).delete()
            message = f"已删除所有 {deleted_count} 条消息"

        elif action == "keep_latest" and keep_latest > 0:
            # 保留最近N个会话
            # 1. 先获取所有会话ID及最新消息时间
            from sqlalchemy import func
            session_stats = db.query(
                ChatMessage.session_id,
                func.max(ChatMessage.created_at).label('last_activity')
            ).group_by(ChatMessage.session_id).order_by(
                func.max(ChatMessage.created_at).desc()
            ).all()

            # 2. 确定要保留的会话
            sessions_to_keep = [s[0] for s in session_stats[:keep_latest]]

            # 3. 删除其他会话
            if sessions_to_keep:
                deleted_count = db.query(ChatMessage).filter(
                    ~ChatMessage.session_id.in_(sessions_to_keep)
                ).delete()
            else:
                deleted_count = 0

            message = f"已删除除最近 {keep_latest} 个会话外的所有消息，共 {deleted_count} 条"

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的操作类型: {action}"
            )

        db.commit()
        total_after = db.query(ChatMessage).count()

        print(f"[会话管理] {message}")

        return {
            "status": "success",
            "action": action,
            "deleted_count": deleted_count,
            "remaining_count": total_after,
            "message": message
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"[会话管理] 删除失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除操作失败: {str(e)}"
        )


@app.delete("/api/sessions/batch")
async def delete_sessions_batch(
        request: BatchDeleteRequest,
        db: Session = Depends(get_db)
):
    """
    批量删除指定会话
    """
    try:
        if not request.session_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请指定要删除的会话ID列表"
            )

        if request.confirm_password != "CONFIRM_DELETE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="需要确认密码 'CONFIRM_DELETE' 才能执行批量删除"
            )

        deleted_count = 0
        for session_id in request.session_ids:
            count = db.query(ChatMessage).filter(
                ChatMessage.session_id == session_id
            ).delete()
            deleted_count += count
            print(f"[批量删除] 删除会话 {session_id}: {count} 条消息")

        db.commit()

        return {
            "status": "success",
            "deleted_sessions": len(request.session_ids),
            "deleted_messages": deleted_count,
            "message": f"已批量删除 {len(request.session_ids)} 个会话，共 {deleted_count} 条消息"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量删除失败: {str(e)}"
        )



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

        # 安全处理时间字段
        created_at = None
        if first_message and first_message.created_at:
            created_at = first_message.created_at.isoformat()

        last_activity = None
        if last_message and last_message.created_at:
            last_activity = last_message.created_at.isoformat()

        summary = {
            "session_id": session_id,
            "total_messages": total_messages,
            "created_at": created_at,
            "last_activity": last_activity,
            "title": first_user_message.content[:50] + "..." if first_user_message and len(
                first_user_message.content) > 50 else (first_user_message.content if first_user_message else "新会话")
        }

        return {
            "session_id": session_id,
            "summary": summary,
            "status": "success"
        }

    except Exception as e:
        print(f"[API Session Summary] 错误: {str(e)}")
        return {
            "session_id": session_id,
            "error": str(e),
            "status": "error"
        }


@app.get("/api/sessions/stats")
async def get_session_statistics(db: Session = Depends(get_db)):
    """
    获取会话统计信息
    """
    try:
        # 总消息数
        total_messages = db.query(ChatMessage).count()

        # 总会话数
        total_sessions = db.query(ChatMessage.session_id).distinct().count()

        # 今日消息数
        from datetime import datetime, timedelta
        today = datetime.utcnow().date()
        today_messages = db.query(ChatMessage).filter(
            func.date(ChatMessage.created_at) == today
        ).count()

        # 消息类型分布
        user_messages = db.query(ChatMessage).filter(
            ChatMessage.role == "user"
        ).count()
        assistant_messages = db.query(ChatMessage).filter(
            ChatMessage.role == "assistant"
        ).count()

        # 最近活跃的会话
        recent_sessions = db.query(
            ChatMessage.session_id,
            func.max(ChatMessage.created_at).label('last_activity'),
            func.count(ChatMessage.id).label('message_count')
        ).group_by(ChatMessage.session_id).order_by(
            func.max(ChatMessage.created_at).desc()
        ).limit(10).all()

        return {
            "status": "success",
            "statistics": {
                "total_messages": total_messages,
                "total_sessions": total_sessions,
                "today_messages": today_messages,
                "message_distribution": {
                    "user": user_messages,
                    "assistant": assistant_messages
                },
                "recent_sessions": [
                    {
                        "session_id": s[0],
                        "last_activity": s[1].isoformat() if s[1] else None,
                        "message_count": s[2]
                    }
                    for s in recent_sessions
                ]
            }
        }

    except Exception as e:
        print(f"[会话统计] 错误: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    # 初始化数据库
    try:
        from database import init_db

        init_db()
        print("✅ 数据库初始化完成")
    except Exception as e:
        print(f"⚠️ 数据库初始化失败: {e}")
        print("⚠️ 继续启动，但数据库可能有问题...")

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