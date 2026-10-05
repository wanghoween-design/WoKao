"""WoKao-ExamAgent (我考) —— 国家考试大纲与 AI 备考作息规划系统。

模块架构：
- `wokao.config`: 全局配置管理
- `wokao.auth`: 认证与会话管理
- `wokao.db`: 数据库会话、模型、标准大纲种子数据与 CRUD
- `wokao.agents`: LangGraph 状态图规划器、AI 伴学导师与鲁棒解析器
- `wokao.services`: 搜索适配器、考情检索管线与爬虫
- `wokao.api`: FastAPI 接口层、数据契约与路由蓝图
"""

__version__ = "2.0.0"
__author__ = "WoKao ExamAgent Team"
