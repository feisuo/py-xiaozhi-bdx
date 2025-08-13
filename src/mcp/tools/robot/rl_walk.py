from __future__ import annotations

import os
import pickle
import time
from threading import Event
from typing import Optional

import numpy as np

from src.robot.mini_bdx_runtime.mini_bdx_runtime.rustypot_position_hwi import HWI
from src.robot.mini_bdx_runtime.mini_bdx_runtime.onnx_infer import OnnxInfer
from src.robot.mini_bdx_runtime.mini_bdx_runtime.raw_imu import Imu
from src.robot.mini_bdx_runtime.mini_bdx_runtime.poly_reference_motion import (
    PolyReferenceMotion,
)
from src.robot.mini_bdx_runtime.mini_bdx_runtime.xbox_controller import XBoxController
from src.robot.mini_bdx_runtime.mini_bdx_runtime.feet_contacts import FeetContacts
from src.robot.mini_bdx_runtime.mini_bdx_runtime.eyes import Eyes
from src.robot.mini_bdx_runtime.mini_bdx_runtime.sounds import Sounds
from src.robot.mini_bdx_runtime.mini_bdx_runtime.antennas import Antennas
from src.robot.mini_bdx_runtime.mini_bdx_runtime.projector import Projector
from src.robot.mini_bdx_runtime.mini_bdx_runtime.rl_utils import (
    LowPassActionFilter,
    make_action_dict,
)
from src.robot.mini_bdx_runtime.mini_bdx_runtime.duck_config import DuckConfig


HOME_DIR = os.path.expanduser("~")


class RLWalk:
    """RL 行走控制，改造以支持外部停止。"""

    def __init__(
        self,
        onnx_model_path: str,
        duck_config_path: str = f"{HOME_DIR}/duck_config.json",
        serial_port: Optional[str] = None,
        control_freq: float = 50,
        pid=[30, 0, 0],
        action_scale=0.25,
        commands=False,
        pitch_bias=0,
        save_obs=False,
        replay_obs=None,
        cutoff_frequency=None,
    ):
        self._stop_event: Event = Event()

        self.duck_config = DuckConfig(config_json_path=duck_config_path, ignore_default=True)

        if serial_port is None:
            serial_port = self.duck_config.serial_port

        self.commands = commands
        self.pitch_bias = pitch_bias

        self.onnx_model_path = onnx_model_path
        self.policy = OnnxInfer(self.onnx_model_path, awd=True)

        self.num_dofs = 14
        self.max_motor_velocity = 5.24

        self.control_freq = control_freq
        self.pid = pid

        self.save_obs = save_obs
        if self.save_obs:
            self.saved_obs = []

        self.replay_obs = replay_obs
        if self.replay_obs is not None:
            self.replay_obs = pickle.load(open(self.replay_obs, "rb"))

        self.action_filter = None
        if cutoff_frequency is not None:
            self.action_filter = LowPassActionFilter(self.control_freq, cutoff_frequency)

        self.hwi = HWI(self.duck_config, serial_port)

        self.start()

        self.imu = Imu(
            sampling_freq=int(self.control_freq),
            user_pitch_bias=self.pitch_bias,
            upside_down=self.duck_config.imu_upside_down,
        )

        self.feet_contacts = FeetContacts()

        self.action_scale = action_scale

        self.last_action = np.zeros(self.num_dofs)
        self.last_last_action = np.zeros(self.num_dofs)
        self.last_last_last_action = np.zeros(self.num_dofs)

        self.init_pos = list(self.hwi.init_pos.values())

        self.motor_targets = np.array(self.init_pos.copy())
        self.prev_motor_targets = np.array(self.init_pos.copy())

        self.last_commands = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

        self.paused = self.duck_config.start_paused

        self.command_freq = 20  # hz
        if self.commands:
            self.xbox_controller = XBoxController(self.command_freq)

        # 使用与当前文件同目录下的系数文件，避免相对工作目录导致找不到文件
        coeff_path = os.path.join(os.path.dirname(__file__), "polynomial_coefficients.pkl")
        self.PRM = PolyReferenceMotion(coeff_path)
        self.imitation_i = 0
        self.imitation_phase = np.array([0, 0])
        self.phase_frequency_factor = 1.0
        self.phase_frequency_factor_offset = self.duck_config.phase_frequency_factor_offset

        if self.duck_config.eyes:
            self.eyes = Eyes()
        if self.duck_config.projector:
            self.projector = Projector()
        if self.duck_config.speaker:
            src_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
            self.sounds = Sounds(volume=1.0, sound_directory=f"{src_root}/robot/mini_bdx_runtime/assets/")
        if self.duck_config.antennas:
            self.antennas = Antennas()

    def get_obs(self):
        imu_data = self.imu.get_data()

        dof_pos = self.hwi.get_present_positions(ignore=["left_antenna", "right_antenna"])
        dof_vel = self.hwi.get_present_velocities(ignore=["left_antenna", "right_antenna"])

        if dof_pos is None or dof_vel is None:
            return None
        if len(dof_pos) != self.num_dofs:
            print(f"ERROR len(dof_pos) != {self.num_dofs}")
            return None
        if len(dof_vel) != self.num_dofs:
            print(f"ERROR len(dof_vel) != {self.num_dofs}")
            return None

        cmds = self.last_commands
        feet_contacts = self.feet_contacts.get()

        obs = np.concatenate(
            [
                imu_data["gyro"],
                imu_data["accelero"],
                cmds,
                dof_pos - self.init_pos,
                dof_vel * 0.05,
                self.last_action,
                self.last_last_action,
                self.last_last_last_action,
                self.motor_targets,
                feet_contacts,
                self.imitation_phase,
            ]
        )
        return obs

    def start(self):
        kps = [self.pid[0]] * 14
        kds = [self.pid[2]] * 14
        kps[5:9] = [8, 8, 8, 8]
        self.hwi.set_kps(kps)
        self.hwi.set_kds(kds)
        self.hwi.turn_on()
        time.sleep(2)

    def stop(self):
        self._stop_event.set()

    def get_phase_frequency_factor(self, x_velocity):
        max_phase_frequency = 1.2
        min_phase_frequency = 1.0
        freq = min_phase_frequency + (abs(x_velocity) / 0.15) * (
            max_phase_frequency - min_phase_frequency
        )
        return freq

    def run(self):
        i = 0
        try:
            print("Starting")
            start_t = time.time()
            while not self._stop_event.is_set():
                left_trigger = 0
                right_trigger = 0
                t = time.time()

                if self.commands:
                    self.last_commands, self.buttons, left_trigger, right_trigger = (
                        self.xbox_controller.get_last_command()
                    )
                    if self.buttons.dpad_up.triggered:
                        self.phase_frequency_factor_offset += 0.05
                        print(
                            f"Phase frequency factor offset {round(self.phase_frequency_factor_offset, 3)}"
                        )
                    if self.buttons.dpad_down.triggered:
                        self.phase_frequency_factor_offset -= 0.05
                        print(
                            f"Phase frequency factor offset {round(self.phase_frequency_factor_offset, 3)}"
                        )
                    if self.buttons.LB.is_pressed:
                        self.phase_frequency_factor = 1.3
                    else:
                        self.phase_frequency_factor = 1.0
                    if self.buttons.X.triggered:
                        if self.duck_config.projector:
                            self.projector.switch()
                    if self.buttons.B.triggered:
                        if self.duck_config.speaker:
                            self.sounds.play_random_sound()
                    if self.duck_config.antennas:
                        self.antennas.set_position_left(right_trigger)
                        self.antennas.set_position_right(left_trigger)
                    if self.buttons.A.triggered:
                        self.paused = not self.paused
                        if self.paused:
                            print("PAUSE")
                        else:
                            print("UNPAUSE")

                if self.paused:
                    time.sleep(0.1)
                    continue

                obs = self.get_obs()
                if obs is None:
                    continue

                self.imitation_i += 1 * (
                    self.phase_frequency_factor + self.phase_frequency_factor_offset
                )
                self.imitation_i = self.imitation_i % self.PRM.nb_steps_in_period
                self.imitation_phase = np.array(
                    [
                        np.cos(self.imitation_i / self.PRM.nb_steps_in_period * 2 * np.pi),
                        np.sin(self.imitation_i / self.PRM.nb_steps_in_period * 2 * np.pi),
                    ]
                )

                if self.save_obs:
                    self.saved_obs.append(obs)

                if self.replay_obs is not None:
                    if i < len(self.replay_obs):
                        obs = self.replay_obs[i]
                    else:
                        print("BREAKING ")
                        break

                action = self.policy.infer(obs)

                self.last_last_last_action = self.last_last_action.copy()
                self.last_last_action = self.last_action.copy()
                self.last_action = action.copy()

                self.motor_targets = self.init_pos + action * self.action_scale

                if self.action_filter is not None:
                    self.action_filter.push(self.motor_targets)
                    filtered_motor_targets = self.action_filter.get_filtered_action()
                    if time.time() - start_t > 1:
                        self.motor_targets = filtered_motor_targets

                self.prev_motor_targets = self.motor_targets.copy()

                head_motor_targets = self.last_commands[3:] + self.motor_targets[5:9]
                self.motor_targets[5:9] = head_motor_targets

                action_dict = make_action_dict(
                    self.motor_targets, list(self.hwi.joints.keys())
                )

                self.hwi.set_position_all(action_dict)

                i += 1

                took = time.time() - t
                if (1 / self.control_freq - took) < 0:
                    print(
                        "Policy control budget exceeded by",
                        np.around(took - 1 / self.control_freq, 3),
                    )
                time.sleep(max(0, 1 / self.control_freq - took))

        except KeyboardInterrupt:
            pass
        finally:
            if self.duck_config.antennas:
                self.antennas.stop()
            if self.duck_config.eyes:
                self.eyes.stop()
            if self.duck_config.projector:
                self.projector.stop()
            self.feet_contacts.stop()
            if self.save_obs:
                pickle.dump(self.saved_obs, open("robot_saved_obs.pkl", "wb"))
            print("TURNING OFF")


