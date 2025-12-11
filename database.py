# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import os
import models  # 导入模型，使其被Base知晓

# 使用SQLite数据库，文件名为 robot.db，存放在项目根目录
# 如果你未来要换MySQL或PostgreSQL，只需修改这个连接字符串即可。
DATABASE_URL = "sqlite:///./robot.db"

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite多线程连接需要这个参数
    echo=True
)

# 创建配置好的SessionLocal类，用于产生新的数据库会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建一个线程安全的scoped session（对于Web应用推荐）
# 这样每个请求都能获得独立的session，并在结束后安全关闭。
SessionScoped = scoped_session(SessionLocal)

# 依赖项函数，用于在FastAPI路由中获取数据库会话
def get_db():
    """获取数据库会话的生成器函数，用于依赖注入"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """初始化数据库，创建所有表（如果不存在）"""
    # 注意：这会根据 Base 的所有子类（我们定义的模型）来创建表
    models.Base.metadata.create_all(bind=engine)
    print("数据库表已初始化。")