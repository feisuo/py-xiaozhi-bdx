"""机器人语音指令解析工具函数。"""

from __future__ import annotations

from typing import Dict

from src.utils.logging_config import get_logger
from .service import RLWalkService

logger = get_logger(__name__)


def parse_and_print_robot_command(args: Dict[str, str]) -> str:
    """
    解析中文语音指令并打印识别到的机器人动作。

    支持指令：
    - 向前走
    - 向后走
    - 左转
    - 右转
    - 左移
    - 右移
    - 打开投影灯
    - 关闭投影灯
    - 左右摇头
    - 点头
    - 暂停（停止）
    - 继续（恢复）
    """

    text = (args.get("text") or "").strip().lower()

    # 标准化中文全角/变体简单处理（此处保持最小实现）
    normalized = text.replace("  ", " ")

    action = None

    # 匹配关键词（包含一些常见同义表达）
    if any(k in normalized for k in ["向前走", "前进", "往前", "前走"]):
        action = "向前走"
    elif any(k in normalized for k in ["向后走", "后退", "往后", "后走"]):
        action = "向后走"
    elif any(k in normalized for k in ["左转", "向左转", "往左转"]):
        action = "左转"
    elif any(k in normalized for k in ["右转", "向右转", "往右转"]):
        action = "右转"
    elif any(k in normalized for k in ["左移", "向左移", "左平移", "往左挪"]):
        action = "左移"
    elif any(k in normalized for k in ["右移", "向右移", "右平移", "往右挪"]):
        action = "右移"
    elif any(k in normalized for k in ["打开投影灯", "开投影灯", "打开投影", "开投影"]):
        action = "打开投影灯"
    elif any(k in normalized for k in ["关闭投影灯", "关投影灯", "关闭投影", "关投影"]):
        action = "关闭投影灯"
    elif any(k in normalized for k in ["左右摇头", "摇头", "左右摆头"]):
        action = "左右摇头"
    elif any(k in normalized for k in ["点头", "上下点头", "点一下头"]):
        action = "点头"
    elif any(k in normalized for k in ["暂停", "先停", "停一下", "暂停一下", "停止"]):
        action = "暂停"
    elif any(k in normalized for k in ["继续", "恢复", "开始"]):
        action = "继续"
    elif any(k in normalized for k in ["停止", "停止运行", "停止行走", "停止程序", "结束运行", "关闭行走"]):
        action = "停止运行"

    if action:
        # 将语义动作映射到 RLWalk 控制
        SPEED_X = 0.12
        SPEED_Y = 0.12
        YAW_RATE = 0.35
        HEAD_YAW = 0.3
        HEAD_PITCH = -0.2  # 负值更接近"点头"（向下）
        
        # 移动指令的自动停止时间（4步约1.6秒）
        MOVE_DURATION = 1.6

        service = RLWalkService.get_instance()
        control_result = ""

        try:
            if action == "向前走":
                control_result = service.control(lin_x=SPEED_X, resume=True, auto_stop_duration=MOVE_DURATION)
            elif action == "向后走":
                control_result = service.control(lin_x=-SPEED_X, resume=True, auto_stop_duration=MOVE_DURATION)
            elif action == "左转":
                control_result = service.control(yaw=YAW_RATE, resume=True, auto_stop_duration=MOVE_DURATION)
            elif action == "右转":
                control_result = service.control(yaw=-YAW_RATE, resume=True, auto_stop_duration=MOVE_DURATION)
            elif action == "左移":
                control_result = service.control(lin_y=SPEED_Y, resume=True, auto_stop_duration=MOVE_DURATION)
            elif action == "右移":
                control_result = service.control(lin_y=-SPEED_Y, resume=True, auto_stop_duration=MOVE_DURATION)
            elif action == "打开投影灯":
                control_result = service.control(projector_toggle=True)
            elif action == "关闭投影灯":
                control_result = service.control(projector_toggle=True)
            elif action == "左右摇头":
                control_result = service.control(head_yaw=HEAD_YAW)
            elif action == "点头":
                control_result = service.control(head_pitch=HEAD_PITCH)
            elif action == "暂停":
                control_result = service.control(pause=True)
            elif action == "继续":
                control_result = service.control(resume=True)
            elif action == "停止运行":
                control_result = RLWalkService.get_instance().stop()

            msg = f"识别到指令：{action} -> {control_result or '已发送控制指令'}"
            print(msg)
            logger.info(msg)
            return msg
        except Exception as e:
            err = f"执行指令失败：{action}，错误：{e}"
            print(err)
            logger.error(err, exc_info=True)
            return err

    msg = "未识别到有效的机器人动作指令"
    print(msg)
    logger.warning(msg + f"，原始文本：{text}")
    return msg



