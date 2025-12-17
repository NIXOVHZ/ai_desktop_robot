import os
from typing import List, Dict
import httpx
import json
from openai import AsyncOpenAI  # 新增：用于小米MiMo


class DeepSeekClient:
    """DeepSeek API 客户端"""

    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("未找到 DEEPSEEK_API_KEY 环境变量")
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def chat(self, messages: List[Dict], max_tokens: int = 2000) -> str:
        """发送消息给Deepseek并获取回复"""

        # 准备请求数据
        data = {
            "model": "deepseek-chat",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "stream": False
        }

        # 调试日志：查看发送的数据大小
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        print(f"[DeepSeek Client] 发送 {len(messages)} 条上下文消息，共约 {total_chars} 字符，请求 {max_tokens} tokens")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self.base_url, json=data, headers=self.headers)
                response.raise_for_status()
                result = response.json()

                # 提取回复
                ai_reply = result["choices"][0]["message"]["content"]
                usage = result.get("usage", {})

                print(f"[DeepSeek Client] 收到回复，长度: {len(ai_reply)} 字符")
                print(f"[DeepSeek Client] API消耗: {usage.get('total_tokens', 'N/A')} tokens")
                return ai_reply

        except httpx.TimeoutException:
            print("[DeepSeek Client] 错误: 请求超时")
            return "请求超时，请稍后重试。"
        except httpx.HTTPStatusError as e:
            print(f"[DeepSeek Client] 错误: API返回 HTTP {e.response.status_code}")
            return f"[API错误] 状态码 {e.response.status_code}"
        except Exception as e:
            print(f"[DeepSeek Client] 未预期错误: {type(e).__name__}: {e}")
            return "处理AI回复时发生未知错误。"


class MiMoClient:
    """小米MiMo API 客户端"""

    def __init__(self):
        self.api_key = os.getenv("MIMO_API_KEY")
        if not self.api_key:
            raise ValueError("未找到 MIMO_API_KEY 环境变量")

        # 使用OpenAI SDK（兼容MiMo API）
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://api.xiaomimimo.com/v1"
        )
        self.model = "mimo-v2-flash"

    async def chat(self, messages: List[Dict], max_tokens: int = 2000) -> str:
        """发送消息给小米MiMo并获取回复"""

        # 调试日志
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        print(f"[MiMo Client] 发送 {len(messages)} 条上下文消息，共约 {total_chars} 字符")

        try:
            # 调用小米MiMo API（兼容OpenAI格式）
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=min(max_tokens, 4096),  # MiMo可能有token限制
                temperature=0.8,
                top_p=0.95,
                stream=False,
                stop=None,
                frequency_penalty=0,
                presence_penalty=0,
                extra_body={
                    "thinking": {"type": "disabled"}
                }
            )

            ai_reply = response.choices[0].message.content
            print(f"[MiMo Client] 收到回复，长度: {len(ai_reply)} 字符")

            # 如果有使用量信息，打印出来
            if hasattr(response, 'usage'):
                usage = response.usage
                print(f"[MiMo Client] API消耗: {usage.total_tokens if usage else 'N/A'} tokens")

            return ai_reply

        except Exception as e:
            print(f"[MiMo Client] 错误: {type(e).__name__}: {e}")

            # 提供更友好的错误信息
            error_msg = str(e)
            if "401" in error_msg or "403" in error_msg:
                return "认证失败，请检查API密钥是否正确。"
            elif "429" in error_msg:
                return "请求过于频繁，请稍后重试。"
            elif "timeout" in error_msg.lower():
                return "请求超时，请检查网络连接。"
            else:
                return f"小米MiMo服务暂时不可用: {error_msg[:100]}"


class MockAIClient:
    """模拟AI客户端，用于无API密钥时测试"""

    async def chat(self, messages: List[Dict], max_tokens: int = 2000) -> str:
        user_msg = messages[-1]["content"].lower()
        if "你好" in user_msg:
            return "你好！我是你的AI桌面机器人，正在开发中。"
        elif "功能" in user_msg:
            return "我目前可以进行对话，未来我会拥有语音、视觉和动作！"
        else:
            return "这是一个模拟回复。要获取真实AI回复，请在'.env' 文件中配置有效的API密钥。"


def get_llm_client():
    """根据配置返回对应的AI客户端"""
    provider = os.getenv("LLM_PROVIDER", "deepseek").lower().strip()

    print(f"[LLM Client] 请求的提供者是：'{provider}'")

    if provider == "deepseek":
        print("[LLM Client] 正在使用 DeepSeek 客户端。")
        try:
            return DeepSeekClient()
        except ValueError as e:
            print(f"[LLM Client] 警告: {e}")
            print("[LLM Client] 回退到模拟客户端。")
            return MockAIClient()

    elif provider == "mimo":
        print("[LLM Client] 正在使用 小米MiMo 客户端。")
        try:
            return MiMoClient()
        except ValueError as e:
            print(f"[LLM Client] 警告: {e}")
            print("[LLM Client] 回退到模拟客户端。")
            return MockAIClient()

    else:
        print(f"[LLM Client] 警告: 未知的提供者 '{provider}'，使用模拟客户端。")
        return MockAIClient()