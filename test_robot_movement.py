#!/usr/bin/env python3
"""
测试机器人移动指令优化功能
"""

import time
from src.mcp.tools.robot.tools import parse_and_print_robot_command

def test_movement_commands():
    """测试移动指令的自动停止功能"""
    
    # 测试移动指令
    movement_commands = [
        "向前走",
        "向后走", 
        "左移",
        "右移",
        "左转",
        "右转"
    ]
    
    print("=== 测试机器人移动指令优化功能 ===")
    print("现在机器人会在执行移动指令时先走4步然后自动停止")
    print()
    
    for i, command in enumerate(movement_commands, 1):
        print(f"测试 {i}: {command}")
        result = parse_and_print_robot_command({"text": command})
        print(f"结果: {result}")
        print("-" * 50)
        
        # 等待一段时间再测试下一个指令
        if i < len(movement_commands):
            print("等待3秒后测试下一个指令...")
            time.sleep(3)
            print()

if __name__ == "__main__":
    test_movement_commands()
