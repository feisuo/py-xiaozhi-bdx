from __future__ import annotations

import time
from threading import Thread, Timer
from typing import Optional

from src.utils.logging_config import get_logger

from .rl_walk import RLWalk


logger = get_logger(__name__)


class RLWalkService:
    """后台运行 RLWalk 的服务单例。"""

    _instance: Optional["RLWalkService"] = None

    def __init__(self) -> None:
        self._worker: Optional[Thread] = None
        self._rl: Optional[RLWalk] = None
        self._stop_timer: Optional[Timer] = None

    @classmethod
    def get_instance(cls) -> "RLWalkService":
        if cls._instance is None:
            cls._instance = RLWalkService()
        return cls._instance

    def is_running(self) -> bool:
        return self._worker is not None and self._worker.is_alive()

    def start(
        self,
        onnx_model_path: str,
        duck_config_path: str,
        control_freq: int = 50,
        action_scale: float = 0.25,
        pid_p: int = 30,
        pid_i: int = 0,
        pid_d: int = 0,
        pitch_bias: float = 0.0,
        commands: bool = False,
        cutoff_frequency: float | None = None,
    ) -> str:
        if self.is_running():
            return "RLWalk 已在运行"

        logger.info("[RLWalkService] 启动 RLWalk")
        self._rl = RLWalk(
            onnx_model_path=onnx_model_path,
            duck_config_path=duck_config_path,
            control_freq=control_freq,
            action_scale=action_scale,
            pid=[pid_p, pid_i, pid_d],
            commands=commands,
            pitch_bias=pitch_bias,
            cutoff_frequency=cutoff_frequency,
        )

        def _run():
            try:
                assert self._rl is not None
                self._rl.run()
            except Exception as e:
                logger.error(f"[RLWalkService] 运行异常: {e}", exc_info=True)
            finally:
                logger.info("[RLWalkService] 运行结束")

        self._worker = Thread(target=_run, daemon=True)
        self._worker.start()
        return "RLWalk 启动成功"

    def stop(self) -> str:
        if not self.is_running():
            return "RLWalk 未在运行"
        assert self._rl is not None
        self._rl.stop()
        return "RLWalk 停止中"
    
    def _cancel_stop_timer(self):
        """取消定时停止计时器"""
        if self._stop_timer and self._stop_timer.is_alive():
            self._stop_timer.cancel()
            self._stop_timer = None
    
    def _schedule_stop(self, duration: float):
        """安排定时停止"""
        self._cancel_stop_timer()
        self._stop_timer = Timer(duration, self._auto_stop)
        self._stop_timer.daemon = True
        self._stop_timer.start()
    
    def _auto_stop(self):
        """自动停止移动"""
        if self.is_running() and self._rl is not None:
            # 停止移动，但保持机器人运行
            self._rl.last_commands[0] = 0.0  # lin_x
            self._rl.last_commands[1] = 0.0  # lin_y
            self._rl.last_commands[2] = 0.0  # yaw
            logger.info("[RLWalkService] 移动指令执行完毕，已停止移动")

    def status(self) -> dict:
        return {
            "running": self.is_running(),
        }

    # ---- High-level control wrapper for MCP ----
    def control(
        self,
        lin_x: float = 0.0,
        lin_y: float = 0.0,
        yaw: float = 0.0,
        head_pitch: float = 0.0,
        head_yaw: float = 0.0,
        head_roll: float = 0.0,
        antennas_left: float = 0.0,
        antennas_right: float = 0.0,
        projector_toggle: bool = False,
        play_sound: bool = False,
        pause: bool = False,
        resume: bool = False,
        auto_stop_duration: float = 0.0,
    ) -> str:
        rl = self._rl
        if not self.is_running() or rl is None:
            return "RLWalk 未在运行"

        # set motion commands
        rl.last_commands[0] = float(lin_x)
        rl.last_commands[1] = float(lin_y)
        rl.last_commands[2] = float(yaw)
        rl.last_commands[4] = float(head_pitch)
        rl.last_commands[5] = float(head_yaw)
        rl.last_commands[6] = float(head_roll)

        # effect actuations not tied to controller
        if hasattr(rl, "duck_config") and rl.duck_config.antennas and hasattr(rl, "antennas"):
            try:
                rl.antennas.set_position_left(float(antennas_left))
                rl.antennas.set_position_right(float(antennas_right))
            except Exception:
                logger.warning("[RLWalkService] 设置天线位置失败", exc_info=True)

        if projector_toggle and hasattr(rl, "duck_config") and rl.duck_config.projector and hasattr(rl, "projector"):
            try:
                rl.projector.switch()
            except Exception:
                logger.warning("[RLWalkService] 切换投影灯失败", exc_info=True)

        if play_sound and hasattr(rl, "duck_config") and rl.duck_config.speaker and hasattr(rl, "sounds"):
            try:
                rl.sounds.play_random_sound()
            except Exception:
                logger.warning("[RLWalkService] 播放声音失败", exc_info=True)

        if pause:
            rl.paused = True
        if resume:
            rl.paused = False

        # 如果设置了自动停止时间，安排定时停止
        if auto_stop_duration > 0:
            self._schedule_stop(auto_stop_duration)

        return "RLWalk 控制指令已下发"


