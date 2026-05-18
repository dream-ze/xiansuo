#!/usr/bin/env python3
"""Loan Radar 一键 Demo 数据初始化脚本。

生成完整演示数据：监控源、帖子、评论、线索、同行账号、日报。
所有数据标记 raw_data.demo = true，支持重复运行（先清理旧 demo 数据）。

用法：
    cd backend
    python scripts/seed_demo_data.py

环境变量：
    DATABASE_URL  数据库连接串（默认从 .env 读取）
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.services.demo_seed_service import seed_demo_data


def main() -> dict:
    db = SessionLocal()
    try:
        print("Loan Radar Demo 数据初始化")
        print("=" * 50)

        print("\n[1/6] 清理旧 demo 数据...")
        stats = seed_demo_data(db)
        cleaned = stats.get("cleaned", {})
        if any(v > 0 for v in cleaned.values()):
            print(f"  清理: sources={cleaned.get('sources', 0)}, comments={cleaned.get('comments', 0)}")
        else:
            print("  无旧数据需清理")

        print(f"\n[2/6] 创建监控源: {stats['sources']}")
        print(f"[3/6] 创建帖子: {stats['posts']}, 评论: {stats['comments']}, 线索: {stats['leads']}")
        levels = stats.get("lead_levels", {})
        print(f"  线索等级分布: A={levels.get('A', 0)}, B={levels.get('B', 0)}, C={levels.get('C', 0)}, D={levels.get('D', 0)}")
        print(f"[4/6] 创建同行账号: {stats['competitors']}")
        print(f"[5/6] 创建采集任务: {stats['crawl_tasks']}")
        print(f"[6/6] 生成今日报告: {stats['report_date']}")

        print("\n" + "=" * 50)
        print("Demo 数据初始化完成！")
        print(f"  监控源: {stats['sources']}")
        print(f"  帖子: {stats['posts']}")
        print(f"  评论: {stats['comments']}")
        print(f"  线索: {stats['leads']} (A={levels.get('A', 0)}, B={levels.get('B', 0)}, C={levels.get('C', 0)}, D={levels.get('D', 0)})")
        print(f"  同行账号: {stats['competitors']}")
        print(f"  采集任务: {stats['crawl_tasks']}")
        print(f"  日报: {stats['report_date']}")
        print("=" * 50)

        return stats
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    result = main()
    if result.get("posts", 0) > 0 and result.get("leads", 0) > 0:
        sys.exit(0)
    else:
        print("\n[ERROR] 数据初始化可能未成功，请检查输出")
        sys.exit(1)
