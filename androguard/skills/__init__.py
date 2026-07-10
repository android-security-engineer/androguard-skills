"""
AndroGuard Skills - 将 AndroGuard 所有核心能力封装为可程序化调用的接口。

支持两种调用模式：
1. Daemon 模式：后台常驻进程，避免重复解析 APK
2. 单次执行模式：无 daemon 时自动降级，每次独立执行

所有方法返回 dict，适合 JSON 序列化输出。
"""

from androguard.skills.main import AndroguardSkillsMain

__all__ = ["AndroguardSkillsMain"]
