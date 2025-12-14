# communication module
import os
import httpx
from typing import List,Dict

from pyexpat.errors import messages


class DeepSeekClient:
    """DeepSeek API 客户端"""

    async def _call_deepseek_api(self, messages: List[Dict], max_tokens: int = 2000) -> str:
        """调用DeepSeek API - 确保足够的回复长度"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                json={
                    "model": "deepseek-chat",
                    "messages": messages,
                    "max_tokens": max_tokens,  # 2000通常是足够的
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()
            data = response.json()

            # 添加日志查看返回的完整内容
            print(f"[LLM] 收到响应，长度: {len(data['choices'][0]['message']['content'])} 字符")
            print(f"[LLM] 回复内容: {data['choices'][0]['message']['content'][:100]}...")

        return data["choices"][0]["message"]["content"]
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/chat/completions"
        self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def chat(self, messages: List[Dict]) -> str:  # 【修正1】参数名改为复数 `messages`
        """发送消息给Deepseek并获取回复"""
        # 【修正1】此处直接使用参数 `messages`，它是从 server.py 传来的正确列表
        data = {
            "model": "deepseek-chat",
            "messages": messages,  # 现在是正确的变量
            "stream": False,
            "max_tokens": 50
        }
        # （可选）可以保留调试打印，但要修正变量名
        # print(f"[LLM Client] 收到 {len(messages)} 条历史消息")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.base_url, json=data, headers=self.headers)

                if response.status_code == 200:
                    # 【修正2】关键：这里是 'message' 不是 'messages'
                    return response.json()["choices"][0]["message"]["content"]
                else:
                    # 可以保留详细的错误信息，便于调试
                    error_detail = response.text[:200] if response.text else "无详细信息"
                    return f"[DeepSeek API错误] 状态码 {response.status_code}，详情: {error_detail}"

        except httpx.TimeoutException:
            return "请求DeepSeek API超时，请检查网络连接或稍后重试。"
        except Exception as e:
            # 打印异常有助于调试
            print(f"[LLM Client] 未预期错误: {e}")
            return "处理AI回复时发生未知错误。"

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
    print(f"[LLM Client] 请求的提供者是：'{provider}'")  # 添加这行
    if provider == "deepseek":
        print("[LLM Client] 正在使用 DeepSeek 客户端。")  # 添加这行
        return DeepSeekClient()
    else:
        print("[LLM Client] 正在使用模拟客户端。")  # 添加这行
        return MockAIClient()
