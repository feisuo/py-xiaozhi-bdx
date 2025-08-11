"""机器人控制工具包.

提供解析中文语音指令并输出识别动作的工具。
"""

from .manager import RobotToolsManager, get_robot_manager

__all__ = [
    "RobotToolsManager",
    "get_robot_manager",
]



