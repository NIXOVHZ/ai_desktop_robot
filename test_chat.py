# test_chat.py
import requests
import json


def test_chat():
    url = "http://localhost:8000/chat"

    # 第一次对话 - 应该创建新会话
    data1 = {
        "message": "我的爱好是读书和编程，你有什么建议吗？",
        "user_id": "test_user_001"
    }

    response1 = requests.post(url, json=data1)
    print("第一次对话回复:")
    print(f"会话ID: {response1.json().get('session_id')}")
    print(f"回复: {response1.json().get('reply')}")
    print("---")

    # 第二次对话 - 使用相同的会话ID
    data2 = {
        "message": "我特别喜欢Python编程，能给我推荐一些进阶书籍吗？",
        "session_id": response1.json().get('session_id')
    }

    response2 = requests.post(url, json=data2)
    print("第二次对话回复:")
    print(f"会话ID: {response2.json().get('session_id')}")
    print(f"回复: {response2.json().get('reply')}")


if __name__ == "__main__":
    test_chat()