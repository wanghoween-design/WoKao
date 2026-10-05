"""wokao.security.crypto — BYOK API Key 静态加密（Fernet + 本机密钥文件）。

设计要点：
- 密钥文件 `.wokao_secret.key` 位于项目根目录（已被 .gitignore 排除），
  首次使用时自动生成；支持 `WOKAO_SECRET_FILE` 环境变量覆盖路径。
- 存储格式：`enc:v1:<fernet-token>`；无前缀的历史明文读取时透明放行（兼容迁移），
  下一次保存时自动升级为密文。
- 密钥文件损坏时快速失败（明确报错），避免静默解出错误数据。
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRET_FILE: Path = Path(os.getenv("WOKAO_SECRET_FILE") or (_BASE_DIR / ".wokao_secret.key"))

_PREFIX = "enc:v1:"
_fernet: Fernet | None = None


def _load_key() -> bytes:
    """读取或创建本机密钥文件（O_EXCL 防并发双写竞态）。"""
    if SECRET_FILE.exists():
        key = SECRET_FILE.read_bytes().strip()
        if key:
            try:
                Fernet(key)
                return key
            except Exception as exc:
                raise RuntimeError(
                    f"密钥文件 {SECRET_FILE} 已损坏，无法解密已保存的模型配置。"
                    f"请删除该文件后重新保存各用户的模型配置。原因：{exc}"
                ) from exc

    key = Fernet.generate_key()
    try:
        fd = os.open(str(SECRET_FILE), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(key)
    except FileExistsError:
        key = SECRET_FILE.read_bytes().strip()
    return key


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_load_key())
    return _fernet


def encrypt_secret(plain: str) -> str:
    """明文 → 'enc:v1:<token>'；空值原样返回；已加密内容幂等。"""
    if not plain:
        return ""
    if plain.startswith(_PREFIX):
        return plain
    token = _get_fernet().encrypt(plain.encode("utf-8")).decode("ascii")
    return _PREFIX + token


def decrypt_secret(stored: str) -> str:
    """'enc:v1:<token>' → 明文。

    - 历史明文（无前缀）：透明放行，等待下次保存时升级为密文；
    - 解密失败（密钥轮换/丢失）：返回空串并告警，调用方按"未配置"降级。
    """
    if not stored:
        return ""
    if not stored.startswith(_PREFIX):
        return stored
    try:
        return _get_fernet().decrypt(stored[len(_PREFIX):].encode("ascii")).decode("utf-8")
    except Exception as exc:
        logger.warning("解密失败（密钥可能已丢失或被更换），该配置将按未配置处理：%s", exc)
        return ""
