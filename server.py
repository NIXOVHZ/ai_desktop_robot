#main server
# server.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from llm_client import get_llm_client
import uvicorn
from dotenv import load_dotenv

from database import get_db
from models import ChatMessage
from sqlalchemy.orm import Session
from fastapi import Depends  # 用于依赖注入

# 加载 .env 文件中的配置
load_dotenv()

# server.py 顶部附近，在 load_dotenv() 之后添加
import os
load_dotenv()
print("=== 环境变量检查 ===") # 添加这行
print(f"LLM_PROVIDER 的值是：{os.getenv('LLM_PROVIDER')}") # 添加这行
print(f"DEEPSEEK_API_KEY 的前几位是：{os.getenv('DEEPSEEK_API_KEY', '未找到')[:10]}...") # 添加这行，只显示前10位以防泄露
print("==================") # 添加这行



app = FastAPI(title="AI桌面机器人服务器")

# 允许网页跨域访问（重要！）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 用于存储简单的对话历史（实际项目请用数据库）
conversation_history = {}

class ChatRequest(BaseModel):
    message: str
    user_id: str = "default_user"

@app.post("/chat")
async def chat_api(
    request: ChatRequest,
    db: Session = Depends(get_db)  # 依赖注入，自动提供会话，请求结束后自动关闭
):
    # 1. 保存用户消息到数据库
    user_msg = ChatMessage(
        session_id=request.user_id,
        role="user",
        content=request.message
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # 2. 构建对话历史（从数据库查询最近的N条）
    history_messages = db.query(ChatMessage) \
        .filter(ChatMessage.session_id == request.user_id) \
        .order_by(ChatMessage.created_at.desc()) \
        .limit(10) \
        .all()
    # 注意：查询结果是时间倒序，可能需要反转来构建正确的messages列表
    history_messages.reverse()

   # 3. 将数据库记录格式化为llm_client所需的messages格式
    messages_for_ai = [
       {"role": msg.role, "content": msg.content}
       for msg in history_messages
   ]

    # =========== 临时替换开始 ===========
    # # 直接使用当前用户消息，跳过数据库历史，用于验证API
    # messages_for_ai = [
    #     {"role": "user", "content": request.message}
    # ]
    # # =========== 临时替换结束 ===========

    # 4. 调用AI获取回复
    client = get_llm_client()
    # print(" === 调试：发送给AI的消息列表 ===")  # 正确：所有的 " "
    # print(f"变量 `messages_for_ai` 的类型是：{type(messages_for_ai)}")  # 正确：所有的 " "
    # print(f"变量 `messages_for_ai` 的完整内容是：")
    # import json
    # print(json.dumps(messages_for_ai, indent=2, ensure_ascii=False))
    # print(" === 调试结束 ===")
    ai_reply = await client.chat(messages_for_ai)

    # 5. 保存AI回复到数据库
    ai_msg = ChatMessage(
        session_id=request.user_id,
        role="assistant",
        content=ai_reply
    )
    db.add(ai_msg)
    db.commit()

    return {"reply": ai_reply, "history_length": len(history_messages) + 1}

@app.get("/")
def root():
    return {"message": "AI桌面机器人服务器已启动！", "docs_url": "http://localhost:8000/docs"}

if __name__ == "__main__":
    # 启动服务器，访问 http://localhost:8000
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)