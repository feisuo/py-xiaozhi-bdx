#!/usr/bin/env python3
"""
测试机器人服务状态
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.mcp.tools.robot.service import RLWalkService

def main():
    """主函数"""
    print("=== 机器人服务状态检查 ===")
    
    # 获取服务实例
    service = RLWalkService.get_instance()
    
    # 检查服务状态
    status = service.status()
    print(f"服务状态: {status}")
    print(f"是否运行: {service.is_running()}")
    
    if not service.is_running():
        print("\n⚠️  机器人服务未运行！")
        print("需要先启动机器人服务才能执行移动指令。")
        print("\n可能的解决方案：")
        print("1. 确保机器人硬件已连接")
        print("2. 启动机器人服务")
        print("3. 检查配置文件")
    else:
        print("\n✅ 机器人服务正在运行")
    
    print("\n=== 测试控制指令 ===")
    
    # 测试一个简单的控制指令
    try:
        result = service.control(lin_x=0.0, lin_y=0.0, yaw=0.0)
        print(f"控制指令结果: {result}")
    except Exception as e:
        print(f"控制指令失败: {e}")

if __name__ == "__main__":
    main()
