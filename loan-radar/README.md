# 智获客

智获客是一个面向 Demo 可成交版的获客线索雷达项目。

当前阶段只推进后端主链路的最小可运行闭环：

监控源管理 -> 采集任务 -> Mock 采集 -> 帖子池 -> 评论池 -> 线索识别 -> 线索池 -> 今日获客报告 -> CSV 导出。

## 当前步骤

步骤 0：项目骨架和文档。

本步骤只创建目录结构和基础文档，不实现业务代码、数据库、接口、采集器或前端页面。

## 目录结构

```text
loan-radar/
  backend/
  frontend/
  docs/
  README.md
  CODEX_TASK_RULES.md
  docker-compose.yml
  .gitignore
```

## 文档索引

- `docs/PRD.md`：产品目标、范围和阶段边界。
- `docs/DB_DESIGN.md`：数据库设计说明入口。
- `docs/API.md`：接口设计说明入口。
- `docs/TASK_BACKLOG.md`：任务拆分和优先级清单。
- `CODEX_TASK_RULES.md`：Codex 开发规则和限制。
