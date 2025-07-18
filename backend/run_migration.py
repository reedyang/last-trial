#!/usr/bin/env python3
"""
运行数据库迁移的快捷脚本
"""

import os
import sys

# 切换到backend目录
backend_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(backend_dir)

# 运行迁移
if __name__ == "__main__":
    import subprocess
    try:
        result = subprocess.run([sys.executable, "migrate_database.py"], check=True)
        print("\n✅ 迁移执行完成")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 迁移执行失败: {e}")
        sys.exit(1) 