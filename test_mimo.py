# test_mimo.py
import asyncio
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


async def test_mimo():
    # 测试小米MiMo客户端
    from llm_client import MiMoClient

    try:
        client = MiMoClient()

        messages = [
            {"role": "user", "content": "你好，请用中文简单介绍一下自己"}
        ]

        response = await client.chat(messages)
        print("小米MiMo回复:")
        print(response)
        return True
    except Exception as e:
        print(f"测试失败: {e}")
        return False


async def test_deepseek():
    # 测试DeepSeek客户端
    from llm_client import DeepSeekClient

    try:
        client = DeepSeekClient()

        messages = [
            {"role": "user", "content": "你好，请用中文简单介绍一下自己"}
        ]

        response = await client.chat(messages)
        print("DeepSeek回复:")
        print(response)
        return True
    except Exception as e:
        print(f"测试失败: {e}")
        return False


async def main():
    provider = os.getenv("LLM_PROVIDER", "deepseek").lower()

    print(f"当前配置的提供商: {provider}")
    print("-" * 50)

    if provider == "mimo":
        await test_mimo()
    elif provider == "deepseek":
        await test_deepseek()
    else:
        print(f"未知的提供商: {provider}")


if __name__ == "__main__":
    asyncio.run(main())