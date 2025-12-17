from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base  # 从models导入Base

# SQLite数据库路径
DATABASE_URL = "sqlite:///./robot.db"

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=True  # 设置为False可以减少日志输出
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """依赖注入，获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表已初始化")