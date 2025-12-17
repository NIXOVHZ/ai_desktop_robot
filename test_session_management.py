# test_session_management.py
import requests
import json


class SessionManagerTester:
    BASE_URL = "http://localhost:8000"

    def __init__(self):
        self.session = requests.Session()

    def test_delete_all(self):
        """测试删除所有会话"""
        print("\n=== 测试删除所有会话 ===")

        # 测试1: 没有确认密码应该失败
        print("测试1: 没有确认密码...")
        response = self.session.delete(f"{self.BASE_URL}/api/sessions?action=all")
        print(f"结果: {response.status_code} - {response.json()}")

        # 测试2: 有确认密码应该成功
        print("\n测试2: 有确认密码...")
        response = self.session.delete(f"{self.BASE_URL}/api/sessions?action=all&confirm=CONFIRM_DELETE")
        print(f"结果: {response.status_code} - {response.json()}")

        return response.status_code == 200

    def test_keep_latest(self):
        """测试保留最近N个会话"""
        print("\n=== 测试保留最近N个会话 ===")

        response = self.session.delete(
            f"{self.BASE_URL}/api/sessions?action=keep_latest&keep_latest=3&confirm=CONFIRM_DELETE")
        print(f"结果: {response.status_code} - {response.json()}")

        return response.status_code == 200

    def test_batch_delete(self):
        """测试批量删除"""
        print("\n=== 测试批量删除 ===")

        # 先获取一些会话
        response = self.session.get(f"{self.BASE_URL}/api/sessions?page_size=10")
        sessions = response.json().get("sessions", [])

        if len(sessions) < 2:
            print("需要至少2个会话进行测试")
            return False

        # 取前2个会话进行删除测试
        session_ids = [s["session_id"] for s in sessions[:2]]

        payload = {
            "session_ids": session_ids,
            "confirm_password": "CONFIRM_DELETE"
        }

        response = self.session.delete(
            f"{self.BASE_URL}/api/sessions/batch",
            json=payload
        )

        print(f"结果: {response.status_code} - {response.json()}")
        return response.status_code == 200

    def test_session_stats(self):
        """测试会话统计"""
        print("\n=== 测试会话统计 ===")

        response = self.session.get(f"{self.BASE_URL}/api/sessions/stats")
        print(f"结果: {response.status_code}")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))

        return response.status_code == 200

    def run_all_tests(self):
        """运行所有测试"""
        print("开始会话管理功能测试...")

        tests = [
            ("删除所有会话", self.test_delete_all),
            ("保留最近N个会话", self.test_keep_latest),
            ("批量删除", self.test_batch_delete),
            ("会话统计", self.test_session_stats),
        ]

        results = []
        for test_name, test_func in tests:
            try:
                success = test_func()
                results.append((test_name, success))
                print(f"{test_name}: {'✅ 通过' if success else '❌ 失败'}")
            except Exception as e:
                print(f"{test_name}: ❌ 异常 - {e}")
                results.append((test_name, False))

        print("\n=== 测试总结 ===")
        for test_name, success in results:
            print(f"{test_name}: {'✅ 通过' if success else '❌ 失败'}")

        passed = sum(1 for _, success in results if success)
        total = len(results)

        print(f"\n通过率: {passed}/{total} ({passed / total * 100:.1f}%)")
        return all(success for _, success in results)


if __name__ == "__main__":
    tester = SessionManagerTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)