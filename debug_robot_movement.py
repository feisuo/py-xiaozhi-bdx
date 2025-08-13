#!/usr/bin/env python3
"""
调试机器人移动指令功能
"""

import time
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.mcp.tools.robot.tools import parse_and_print_robot_command
from src.mcp.tools.robot.service import RLWalkService

def test_service_status():
    """测试服务状态"""
    print("=== 测试 RLWalkService 状态 ===")
    service = RLWalkService.get_instance()
    status = service.status()
    print(f"服务状态: {status}")
    print(f"是否运行: {service.is_running()}")
    print()

def test_single_movement():
    """测试单个移动指令"""
    print("=== 测试单个移动指令 ===")
    
    # 测试向前走指令
    command = "向前走"
    print(f"发送指令: {command}")
    
    start_time = time.time()
    result = parse_and_print_robot_command({"text": command})
    end_time = time.time()
    
    print(f"指令执行时间: {end_time - start_time:.2f}秒")
    print(f"执行结果: {result}")
    print()
    
    # 等待自动停止
    print("等待自动停止...")
    time.sleep(3)
    
    # 检查服务状态
    service = RLWalkService.get_instance()
    if service.is_running():
        print("机器人仍在运行")
    else:
        print("机器人已停止运行")
    print()

def test_multiple_movements():
    """测试多个移动指令"""
    print("=== 测试多个移动指令 ===")
    
    commands = ["向前走", "向后走", "左移", "右移"]
    
    for i, command in enumerate(commands, 1):
        print(f"测试 {i}/{len(commands)}: {command}")
        
        start_time = time.time()
        result = parse_and_print_robot_command({"text": command})
        end_time = time.time()
        
        print(f"执行时间: {end_time - start_time:.2f}秒")
        print(f"结果: {result}")
        
        # 等待指令执行完毕
        print("等待指令执行完毕...")
        time.sleep(2)
        print("-" * 50)

def main():
    """主函数"""
    print("机器人移动指令调试工具")
    print("=" * 50)
    
    # 测试服务状态
    test_service_status()
    
    # 测试单个移动指令
    test_single_movement()
    
    # 测试多个移动指令
    test_multiple_movements()
    
    print("调试完成")

if __name__ == "__main__":
    main()
