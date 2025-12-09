#main server
# server.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from llm_client import get_llm_client
import uvicorn
import os
from dotenv import load_dotenv

# 加载 .env 文件中的配置
load_dotenv()

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
async def chat_api(request: ChatRequest):
    """核心聊天接口"""
    user_id = request.user_id
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    # 1. 将用户消息加入历史
    conversation_history[user_id].append({"role": "user", "content": request.message})

    # 2. 调用AI获取回复
    client = get_llm_client()
    ai_reply = await client.chat(conversation_history[user_id])

    # 3. 将AI回复加入历史
    conversation_history[user_id].append({"role": "assistant", "content": ai_reply})

    # 4. 保持历史长度，避免过长
    if len(conversation_history[user_id]) > 20:
        conversation_history[user_id] = conversation_history[user_id][-20:]

    return {"reply": ai_reply, "history_length": len(conversation_history[user_id])}

@app.get("/")
def root():
    return {"message": "AI桌面机器人服务器已启动！", "docs_url": "http://localhost:8000/docs"}

if __name__ == "__main__":
    # 启动服务器，访问 http://localhost:8000
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)