# clean_db.py
from database import SessionLocal
from models import ChatMessage

def clean_test_data():
    db = SessionLocal()
    try:
        # 删除所有会话ID为'test'或'default_user'的记录
        count = db.query(ChatMessage)\
            .filter(ChatMessage.session_id.in_(['test', 'default_user']))\
            .delete()
        db.commit()
        print(f"已删除 {count} 条测试记录")
    finally:
        db.close()

if __name__ == "__main__":
    clean_test_data()