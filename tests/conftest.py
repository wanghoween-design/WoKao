"""tests/conftest.py — 测试全局夹具：会话级临时数据库与密钥文件。

WOKAO_DB_PATH / WOKAO_SECRET_FILE 必须在任何 wokao 模块导入之前设置
（wokao.db.session.DB_PATH 与 wokao.security.crypto.SECRET_FILE 均在导入期求值）。
pytest 保证 conftest 先于所有测试模块加载，因此在模块顶层设置即可。
测试全程不触碰项目根目录的真实 wokao.db 与 .wokao_secret.key。
"""
import atexit
import os
import shutil
import tempfile
from pathlib import Path

_TMP_DIR = Path(tempfile.mkdtemp(prefix="wokao-test-"))
os.environ["WOKAO_DB_PATH"] = str(_TMP_DIR / "wokao-test.db")
os.environ["WOKAO_SECRET_FILE"] = str(_TMP_DIR / "test-secret.key")


def _cleanup() -> None:
    shutil.rmtree(_TMP_DIR, ignore_errors=True)


atexit.register(_cleanup)

# 显式初始化表结构，避免依赖其他测试模块先导入 server 触发 init_db
from wokao.db.models import init_db  # noqa: E402

init_db()
