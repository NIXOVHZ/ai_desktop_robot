# fix_none_timestamps.py
from database import SessionLocal
from models import ChatMessage
from datetime import datetime


def fix_none_timestamps():
    """修复数据库中 created_at 为 None 的记录"""
    db = SessionLocal()

    try:
        # 查找 created_at 为 None 的记录
        null_records = db.query(ChatMessage).filter(ChatMessage.created_at.is_(None)).all()

        print(f"找到 {len(null_records)} 条 created_at 为 None 的记录")

        # 更新这些记录
        for record in null_records:
            print(f"修复记录 {record.id} (会话: {record.session_id})")
            record.created_at = datetime.utcnow()

        if null_records:
            db.commit()
            print(f"✅ 已修复 {len(null_records)} 条记录")
        else:
            print("✅ 没有需要修复的记录")

    except Exception as e:
        print(f"❌ 修复失败: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    fix_none_timestamps()