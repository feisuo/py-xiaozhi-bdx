"""机器人控制工具管理器.

负责注册用于解析语音指令并打印机器人动作的工具。
"""

from typing import Any, Dict, Optional

from src.utils.logging_config import get_logger

from .tools import parse_and_print_robot_command
from .service import RLWalkService

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
            self._register_rlwalk_tools(add_tool, PropertyList, Property, PropertyType)
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
                "识别并打印机器人动作指令。支持：向前走、向后走、左转、右转、左移、右移、打开投影灯、左右摇头、点头。",
                props,
                parse_and_print_robot_command,
            )
        )

    def _register_rlwalk_tools(self, add_tool, PropertyList, Property, PropertyType) -> None:
        """注册 RLWalk 相关工具。"""
        # start
        start_props = PropertyList(
            [
                Property("onnx_model_path", PropertyType.STRING),
                Property("duck_config_path", PropertyType.STRING),
                Property("control_freq", PropertyType.INTEGER, default_value=50),
                Property("action_scale", PropertyType.STRING, default_value="0.25"),
                Property("pid_p", PropertyType.INTEGER, default_value=30),
                Property("pid_i", PropertyType.INTEGER, default_value=0),
                Property("pid_d", PropertyType.INTEGER, default_value=0),
                Property("pitch_bias", PropertyType.STRING, default_value="0"),
                Property("commands", PropertyType.BOOLEAN, default_value=False),
                Property("cutoff_frequency", PropertyType.STRING, default_value=""),
            ]
        )

        def _to_float(value: Any, default: float | None) -> float | None:
            if value is None:
                return default
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                val = value.strip()
                if val == "":
                    return default
                try:
                    return float(val)
                except Exception:
                    return default
            return default

        def start_cb(args: Dict[str, Any]) -> str:
            cutoff = _to_float(args.get("cutoff_frequency"), None)
            return RLWalkService.get_instance().start(
                onnx_model_path=args["onnx_model_path"],
                duck_config_path=args["duck_config_path"],
                control_freq=args["control_freq"],
                action_scale=_to_float(args.get("action_scale"), 0.25) or 0.25,
                pid_p=args.get("pid_p", 30),
                pid_i=args.get("pid_i", 0),
                pid_d=args.get("pid_d", 0),
                pitch_bias=_to_float(args.get("pitch_bias"), 0.0) or 0.0,
                commands=bool(args.get("commands", False)),
                cutoff_frequency=cutoff,
            )

        add_tool(
            (
                "self.robot.rlwalk.start",
                "启动 RLWalk 机器人行走控制（后台运行）",
                start_props,
                start_cb,
            )
        )

        # stop
        stop_props = PropertyList([])

        def stop_cb(_: Dict[str, Any]) -> str:
            return RLWalkService.get_instance().stop()

        add_tool(("self.robot.rlwalk.stop", "停止 RLWalk 运行", stop_props, stop_cb))

        # status
        status_props = PropertyList([])

        def status_cb(_: Dict[str, Any]) -> str:
            return str(RLWalkService.get_instance().status())

        add_tool(("self.robot.rlwalk.status", "查询 RLWalk 运行状态", status_props, status_cb))

        # control
        control_props = PropertyList(
            [
                Property("lin_x", PropertyType.STRING, default_value="0"),
                Property("lin_y", PropertyType.STRING, default_value="0"),
                Property("yaw", PropertyType.STRING, default_value="0"),
                Property("head_pitch", PropertyType.STRING, default_value="0"),
                Property("head_yaw", PropertyType.STRING, default_value="0"),
                Property("head_roll", PropertyType.STRING, default_value="0"),
                Property("antennas_left", PropertyType.STRING, default_value="0"),
                Property("antennas_right", PropertyType.STRING, default_value="0"),
                Property("projector_toggle", PropertyType.BOOLEAN, default_value=False),
                Property("play_sound", PropertyType.BOOLEAN, default_value=False),
                Property("pause", PropertyType.BOOLEAN, default_value=False),
                Property("resume", PropertyType.BOOLEAN, default_value=False),
            ]
        )

        def _to_float(value: Any, default: float = 0.0) -> float:
            try:
                if isinstance(value, (int, float)):
                    return float(value)
                if isinstance(value, str):
                    return float(value.strip() or default)
            except Exception:
                return default
            return default

        def control_cb(args: Dict[str, Any]) -> str:
            return RLWalkService.get_instance().control(
                lin_x=_to_float(args.get("lin_x", 0)),
                lin_y=_to_float(args.get("lin_y", 0)),
                yaw=_to_float(args.get("yaw", 0)),
                head_pitch=_to_float(args.get("head_pitch", 0)),
                head_yaw=_to_float(args.get("head_yaw", 0)),
                head_roll=_to_float(args.get("head_roll", 0)),
                antennas_left=_to_float(args.get("antennas_left", 0)),
                antennas_right=_to_float(args.get("antennas_right", 0)),
                projector_toggle=bool(args.get("projector_toggle", False)),
                play_sound=bool(args.get("play_sound", False)),
                pause=bool(args.get("pause", False)),
                resume=bool(args.get("resume", False)),
            )

        add_tool(
            (
                "self.robot.rlwalk.control",
                "对正在运行的 RLWalk 进行控制（速度、头部、天线、投影灯、声音、暂停/恢复）",
                control_props,
                control_cb,
            )
        )

    def is_initialized(self) -> bool:
        return self._initialized

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "tools_count": 5,
            "available_tools": [
                "self.robot.parse_command",
                "self.robot.rlwalk.start",
                "self.robot.rlwalk.stop",
                "self.robot.rlwalk.status",
                "self.robot.rlwalk.control",
            ],
        }


_robot_manager: Optional[RobotToolsManager] = None


def get_robot_manager() -> RobotToolsManager:
    global _robot_manager
    if _robot_manager is None:
        _robot_manager = RobotToolsManager()
    return _robot_manager


