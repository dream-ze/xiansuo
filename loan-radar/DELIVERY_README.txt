========================================
  助贷线索雷达 - 交付说明
========================================

快速开始（推荐）
------------------------------------

1. 双击 setup.bat
   - 自动安装 Python 3.12
   - 自动下载 PostgreSQL 便携版（免安装）
   - 自动初始化数据库
   - 自动安装项目依赖
   - 自动构建前端

2. 双击 一键启动.bat
   - 自动启动 PostgreSQL（如未运行）
   - 启动后端服务
   - 浏览器自动打开 http://localhost:8001
   - 只需一个窗口！

Docker 启动（备选）
------------------------------------

1. 安装 Docker Desktop
2. 双击 start.bat
   - 自动构建并启动所有容器
   - 浏览器自动打开 http://localhost

首次使用
------------------------------------

1. 打开页面后点击"注册"，创建账号
2. 生成演示数据（可选）：
   cd backend && python scripts\seed_demo_data.py

默认端口
------------------------------------

生产模式（一键启动.bat）:
  前端+后端:  http://localhost:8001
  数据库:     localhost:5432

开发模式（start-dev.bat）:
  前端:       http://localhost:5173
  后端 API:   http://localhost:8001/docs
  数据库:     localhost:5432

常见问题
------------------------------------

Q: setup.bat 安装 Python 失败？
A: 手动下载安装：https://www.python.org/downloads/
   安装时务必勾选 "Add Python to PATH"

Q: PostgreSQL 下载/启动失败？
A: 1. 检查端口 5432 是否被占用
   2. 或手动安装 PostgreSQL：https://www.postgresql.org/download/windows/
   3. 安装后重新运行 setup.bat

Q: 后端启动后无法访问？
A: 1. 检查后端窗口是否有报错
   2. 确认 PostgreSQL 正在运行
   3. 确认 backend\.env 中 DATABASE_URL 配置正确
   4. 尝试手动启动：cd backend && python -m uvicorn app.main:app --port 8001

Q: 前端页面空白？
A: 1. 确认 frontend\dist 目录存在且有 index.html
   2. 重新构建：cd frontend && npm run build
   3. 或使用开发模式：双击 start-dev.bat

Q: 端口被占用？
A: 修改 backend\.env 中的端口配置，
   或关闭占用端口的程序
