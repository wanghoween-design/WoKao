# 我考 WoKao-ExamAgent - Linux/macOS 一键环境脚本
# 用法： bash setup_env.sh

set -e

PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "==> 创建虚拟环境 .venv"
"$PYTHON_BIN" -m venv .venv

echo "==> 激活虚拟环境"
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> 升级 pip"
python -m pip install --upgrade pip

echo "==> 安装依赖"
pip install -r requirements.txt

echo "==> 完成。下一步："
echo "    1) 配置密钥： export OPENAI_API_KEY=sk-xxx   （可选 export MOCK_LLM=1 离线运行）"
echo "    2) 启动服务： uvicorn server:app --reload --host 0.0.0.0 --port 8000"
echo "    3) 浏览器打开 http://127.0.0.1:8000"
