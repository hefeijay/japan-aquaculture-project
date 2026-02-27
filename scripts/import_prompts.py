#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 db_datas/prompts.csv 导入数据库 prompts 表。

连接方式通过命令行参数指定，未提供时自动回退到 backend/.env 中的配置。

用法示例:
  # 使用 .env 默认连接
  python scripts/import_prompts.py

  # 完全自定义连接
  python scripts/import_prompts.py --host 127.0.0.1 --port 3306 --user root --password secret --db cognitive

  # 指定 CSV 文件路径（默认为脚本同目录下的 db_datas/prompts.csv）
  python scripts/import_prompts.py --csv /path/to/prompts.csv

  # 遇到已存在记录时执行更新（默认跳过）
  python scripts/import_prompts.py --on-conflict update
"""

import argparse
import csv
import os
import sys

# ---------------------------------------------------------------------------
# 依赖检查
# ---------------------------------------------------------------------------
try:
    import pymysql
except ImportError:
    print("错误：未安装 pymysql，请执行 pip install pymysql")
    sys.exit(1)

# ---------------------------------------------------------------------------
# 默认值：从 backend/.env 读取
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
_ENV_PATH = os.path.join(_PROJECT_ROOT, "backend", ".env")


def _load_env(path: str) -> dict:
    """简单解析 .env 文件，返回键值字典（不覆盖已有环境变量）。"""
    env = {}
    if not os.path.exists(path):
        return env
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


_env = _load_env(_ENV_PATH)


def _env_get(key: str, default: str = "") -> str:
    return os.environ.get(key) or _env.get(key, default)


# ---------------------------------------------------------------------------
# CLI 参数
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="将 prompts.csv 导入到 MySQL prompts 表",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host",     default=_env_get("MYSQL_HOST", "localhost"),  help="数据库主机")
    parser.add_argument("--port",     default=int(_env_get("MYSQL_PORT", "3306")), type=int, help="数据库端口")
    parser.add_argument("--user",     default=_env_get("MYSQL_USER", "root"),       help="数据库用户名")
    parser.add_argument("--password", default=_env_get("MYSQL_PASSWORD", ""),       help="数据库密码")
    parser.add_argument("--db",       default=_env_get("MYSQL_DATABASE", "cognitive"), help="数据库名称")
    parser.add_argument(
        "--csv",
        default=os.path.join(_SCRIPT_DIR, "db_datas", "prompts.csv"),
        help="CSV 文件路径",
    )
    parser.add_argument(
        "--on-conflict",
        choices=["skip", "update"],
        default="skip",
        help="遇到已存在记录（agent_name + template_key 唯一）时的处理方式：skip=跳过，update=覆盖更新",
    )
    parser.add_argument("--dry-run", action="store_true", help="仅解析 CSV，不写入数据库")
    return parser


# ---------------------------------------------------------------------------
# 核心导入逻辑
# ---------------------------------------------------------------------------
INSERT_SQL = """
    INSERT INTO prompts (agent_name, template_key, description, version, template)
    VALUES (%(agent_name)s, %(template_key)s, %(description)s, %(version)s, %(template)s)
"""

UPSERT_SQL = """
    INSERT INTO prompts (agent_name, template_key, description, version, template)
    VALUES (%(agent_name)s, %(template_key)s, %(description)s, %(version)s, %(template)s)
    ON DUPLICATE KEY UPDATE
        description = VALUES(description),
        version     = VALUES(version),
        template    = VALUES(template)
"""


def load_csv(csv_path: str) -> list[dict]:
    """读取并解析 CSV，返回行列表。"""
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # 第 1 行是表头
            agent_name = (row.get("agent_name") or "").strip()
            template   = (row.get("template")   or "").strip()
            if not agent_name or not template:
                print(f"  ⚠ 跳过第 {i} 行（agent_name 或 template 为空）")
                continue
            rows.append({
                "agent_name":   agent_name,
                "template_key": (row.get("template_key") or "").strip() or None,
                "description":  (row.get("description")  or "").strip() or None,
                "version":      (row.get("version")      or "").strip() or None,
                "template":     template,
            })
    return rows


def run_import(args: argparse.Namespace) -> None:
    # 1. 检查 CSV
    if not os.path.exists(args.csv):
        print(f"错误：CSV 文件不存在 → {args.csv}")
        sys.exit(1)

    print("=" * 60)
    print("Prompts CSV 导入工具")
    print("=" * 60)
    print(f"  CSV 文件  : {args.csv}")
    print(f"  数据库    : {args.user}@{args.host}:{args.port}/{args.db}")
    print(f"  冲突处理  : {args.on_conflict}")
    print(f"  演习模式  : {'是' if args.dry_run else '否'}")
    print()

    # 2. 解析 CSV
    rows = load_csv(args.csv)
    print(f"共解析到 {len(rows)} 条有效记录。")

    if args.dry_run:
        print("\n[演习模式] 不写入数据库，退出。")
        for r in rows:
            print(f"  agent={r['agent_name']!r:30s}  key={str(r['template_key'])!r:20s}  ver={r['version']!r}")
        return

    if not rows:
        print("没有可导入的数据，退出。")
        return

    # 3. 连接数据库
    print("\n正在连接数据库...")
    try:
        conn = pymysql.connect(
            host=args.host,
            port=args.port,
            user=args.user,
            password=args.password,
            database=args.db,
            charset="utf8mb4",
            autocommit=False,
            connect_timeout=10,
        )
    except pymysql.Error as e:
        print(f"连接失败：{e}")
        sys.exit(1)
    print("  ✓ 连接成功")

    # 4. 执行导入
    sql = UPSERT_SQL if args.on_conflict == "update" else INSERT_SQL
    inserted = updated = skipped = 0

    try:
        with conn.cursor() as cur:
            for row in rows:
                try:
                    affected = cur.execute(sql, row)
                    if args.on_conflict == "update":
                        # ON DUPLICATE KEY UPDATE：affected=1 表示插入，=2 表示更新
                        if affected == 2:
                            updated += 1
                        else:
                            inserted += 1
                    else:
                        inserted += 1
                except pymysql.err.IntegrityError:
                    # skip 模式下遇到唯一键冲突直接跳过
                    skipped += 1
                except pymysql.Error as e:
                    print(f"  ⚠ 写入失败（{row['agent_name']}/{row['template_key']}）：{e}")
                    skipped += 1
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"\n发生异常，已回滚：{e}")
        sys.exit(1)
    finally:
        conn.close()

    # 5. 结果汇报
    print("\n" + "=" * 60)
    print("导入完成！")
    print(f"  新增：{inserted} 条")
    if args.on_conflict == "update":
        print(f"  更新：{updated} 条")
    if skipped:
        print(f"  跳过：{skipped} 条")
    print("=" * 60)


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = build_parser()
    run_import(parser.parse_args())
