# test_api.py 修复版
import asyncio
import os
from dotenv import load_dotenv  # 新增导入

# 新增：加载 .env 文件
load_dotenv()

# 调试：打印环境变量（安全起见只打印前几位）
api_key = os.getenv("DEEPSEEK_API_KEY")
print(f"[测试] 加载到的API密钥前几位: {api_key[:10] if api_key else '未找到'}")

from llm_client import get_llm_client


async def test_api():
    client = get_llm_client()
    messages = [
        {"role": "user", "content": "请用一句话介绍一下你自己"}
    ]

    print("测试API调用...")
    try:
        reply = await client.chat(messages)
        print(f"回复长度: {len(reply)} 字符")
        print(f"完整回复:\n{reply}")
    except Exception as e:
        print(f"错误: {e}")


if __name__ == "__main__":
    asyncio.run(test_api())