# config.py
class SecurityConfig:
    # 删除操作的确认密码
    DELETE_CONFIRM_PASSWORD = "CONFIRM_DELETE"

    # 允许的操作类型
    ALLOWED_DELETE_ACTIONS = ["all", "keep_latest", "selected"]

    # 最大保留会话数
    MAX_KEEP_LATEST = 50

    # 删除操作的冷却时间（秒）
    DELETE_COOLDOWN = 10

    # 记录删除操作日志
    LOG_DELETIONS = True


class SessionConfig:
    # 会话过期时间（天）
    SESSION_EXPIRY_DAYS = 30

    # 最大会话数量限制
    MAX_SESSIONS = 100

    # 最大消息数量限制
    MAX_MESSAGES_PER_SESSION = 1000