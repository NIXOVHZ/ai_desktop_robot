# communication module
import os
import httpx
from typing import List,Dict

class DeepSeekClient:
    """DeepSeek API 客户端"""
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://aip.deepseek.com/chat/completions"
        self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def chat(self, message:list[Dict]) -> str:
        """发送消息给Deepseek并获取回复"""
        data = {"model": "deepseek-chat", "message": message, "stream": False}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.base_url, json=data, headers=self.headers)
                if response.status_code == 200:
                    return response.json()["choices"][0]["messages"]["content"]
                else:
                    return f"抱歉，AI服务器暂时出了点问题（错误吗：{response.status_code})。"
        except Exception:
            return "抱歉，网络连接出现问题，请检查你的网络或API密钥配置。"

class MockAIClient:
    """模拟AI客户端，用于无API密钥时测试"""
    async def chat(self,messages: List[Dict]) -> str:
        user_msg = messages[-1]["content"].lower()
        if "你好" in user_msg:
            return "你好！我是你的AI桌面机器人，正在开发中。"
        elif "功能" in user_msg:
            return "我目前可以进行对话，未来我会拥有语音、视觉和动作！"
        else:
            return "这是一个模拟回复。要获取真实AI回复，请在'.env' 文件中配置有效的Deepseek API 密钥。"

def get_llm_client():
    """根据配置返回对应的AI客户端"""
    provider = os.getenv("LLM_PROVIDER","mock").lower()
    if provider == "deepseek":
        return DeepSeekClient()
    else:
        return MockAIClient()
