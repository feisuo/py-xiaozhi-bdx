"""机器人控制工具管理器.

仅注册语音命令识别相关工具。
"""

from typing import Dict, Optional, Any

from src.utils.logging_config import get_logger

from .tools import parse_and_print_robot_command

logger = get_logger(__name__)


class RobotToolsManager:
    """机器人工具管理器."""

    def __init__(self) -> None:
        self._initialized = False
        logger.info("[RobotManager] 初始化")

    def init_tools(self, add_tool, PropertyList, Property, PropertyType) -> None:
        """初始化并注册机器人工具。"""
        try:
            logger.info("[RobotManager] 开始注册工具")
            self._register_parse_command_tool(add_tool, PropertyList, Property, PropertyType)
            self._initialized = True
            logger.info("[RobotManager] 工具注册完成")
        except Exception as e:
            logger.error(f"[RobotManager] 工具注册失败: {e}", exc_info=True)
            raise

    def _register_parse_command_tool(self, add_tool, PropertyList, Property, PropertyType) -> None:
        """注册语音指令解析工具。"""
        props = PropertyList([
            Property("text", PropertyType.STRING),
        ])
        add_tool(
            (
                "self.robot.parse_command",
                "识别并打印机器人动作指令。支持：向前走、向后走、左转、右转、左移、右移、打开投影灯、关闭投影灯、左右摇头、点头、停止。",
                props,
                parse_and_print_robot_command,
            )
        )

    def is_initialized(self) -> bool:
        return self._initialized

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "tools_count": 1,
            "available_tools": [
                "self.robot.parse_command",
            ],
        }


_robot_manager: Optional[RobotToolsManager] = None


def get_robot_manager() -> RobotToolsManager:
    global _robot_manager
    if _robot_manager is None:
        _robot_manager = RobotToolsManager()
    return _robot_manager


