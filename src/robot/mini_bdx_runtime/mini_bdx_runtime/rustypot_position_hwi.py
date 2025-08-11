import time
import numpy as np
import rustypot
from mini_bdx_runtime.duck_config import DuckConfig
import serial
import serial.tools.list_ports


class HWI:
    def __init__(self, duck_config: DuckConfig, serial_port: str = "/dev/ttyS0", baudrate: int = 1000000):
        self.duck_config = duck_config

        # Order matters here
        self.joints = {
            "left_hip_yaw": 20,
            "left_hip_roll": 21,
            "left_hip_pitch": 22,
            "left_knee": 23,
            "left_ankle": 24,
            "neck_pitch": 30,
            "head_pitch": 31,
            "head_yaw": 32,
            "head_roll": 33,
            # "left_antenna": None,
            # "right_antenna": None,
            "right_hip_yaw": 10,
            "right_hip_roll": 11,
            "right_hip_pitch": 12,
            "right_knee": 13,
            "right_ankle": 14,
        }

        self.zero_pos = {
            "left_hip_yaw": 0,
            "left_hip_roll": 0,
            "left_hip_pitch": 0,
            "left_knee": 0,
            "left_ankle": 0,
            "neck_pitch": 0,
            "head_pitch": 0,
            "head_yaw": 0,
            "head_roll": 0,
            # "left_antenna":0,
            # "right_antenna":0,
            "right_hip_yaw": 0,
            "right_hip_roll": 0,
            "right_hip_pitch": 0,
            "right_knee": 0,
            "right_ankle": 0,
        }

        self.init_pos = {
            "left_hip_yaw": 0.002,
            "left_hip_roll": 0.053,
            "left_hip_pitch": -0.63,
            "left_knee": 1.368,
            "left_ankle": -0.784,
            "neck_pitch": 0.0,
            "head_pitch": 0.0,
            "head_yaw": 0,
            "head_roll": 0,
            # "left_antenna": 0,
            # "right_antenna": 0,
            "right_hip_yaw": -0.003,
            "right_hip_roll": -0.065,
            "right_hip_pitch": 0.635,
            "right_knee": 1.379,
            "right_ankle": -0.796,
        }

        self.joints_offsets = self.duck_config.joints_offset

        self.kps = np.ones(len(self.joints)) * 32  # default kp
        self.kds = np.ones(len(self.joints)) * 0  # default kd
        self.low_torque_kps = np.ones(len(self.joints)) * 2

        # 使用串口连接，支持从配置文件读取串口设置
        if hasattr(duck_config, 'serial_port'):
            serial_port = duck_config.serial_port
        if hasattr(duck_config, 'serial_baudrate'):
            baudrate = duck_config.serial_baudrate
            
        # 初始化串口连接，添加重试机制
        self.io = self._initialize_serial_connection(serial_port, baudrate)
        
        # 缓存上一次成功的数据，用于通信失败时的回退
        self.last_successful_positions = None
        self.last_successful_velocities = None
        self.communication_errors = 0
        self.max_communication_errors = 10

    def _initialize_serial_connection(self, serial_port, baudrate, max_retries=3):
        """初始化串口连接，带重试机制"""
        for attempt in range(max_retries):
            try:
                print(f"Attempting to connect to {serial_port} at {baudrate} baud (attempt {attempt + 1}/{max_retries})")
                
                # 检查串口是否可用
                if not self._check_serial_port(serial_port):
                    print(f"Warning: Serial port {serial_port} not found or not accessible")
                    if attempt == max_retries - 1:
                        raise Exception(f"Serial port {serial_port} not available")
                
                # 尝试创建连接
                io = rustypot.feetech(serial_port, baudrate)
                
                # 测试连接
                try:
                    # 尝试读取一个电机的位置来测试连接
                    test_id = list(self.joints.values())[0]
                    io.read_present_position([test_id])
                    print(f"✓ Successfully connected to {serial_port}")
                    return io
                except Exception as e:
                    print(f"Connection test failed: {e}")
                    if attempt == max_retries - 1:
                        raise Exception(f"Failed to establish communication with motor controller: {e}")
                    
            except Exception as e:
                print(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to initialize serial connection after {max_retries} attempts: {e}")
                time.sleep(1)  # 等待1秒后重试
        
        raise Exception("Failed to initialize serial connection")

    def _check_serial_port(self, port):
        """检查串口是否可用"""
        try:
            # 尝试打开串口
            with serial.Serial(port, timeout=1) as ser:
                return True
        except:
            return False

    def _safe_serial_operation(self, operation, *args, **kwargs):
        """安全的串口操作，带错误处理和重试"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = operation(*args, **kwargs)
                self.communication_errors = 0  # 重置错误计数
                return result
            except Exception as e:
                self.communication_errors += 1
                print(f"Serial communication error (attempt {attempt + 1}/{max_retries}): {e}")
                
                if self.communication_errors > self.max_communication_errors:
                    print("Too many communication errors, returning cached data")
                    return None
                
                if attempt < max_retries - 1:
                    time.sleep(0.1)  # 短暂等待后重试
                else:
                    print(f"Serial operation failed after {max_retries} attempts")
                    return None

    def set_kps(self, kps):
        self.kps = kps
        self._safe_serial_operation(self.io.set_kps, list(self.joints.values()), self.kps)

    def set_kds(self, kds):
        self.kds = kds
        self._safe_serial_operation(self.io.set_kds, list(self.joints.values()), self.kds)

    def set_kp(self, id, kp):
        self._safe_serial_operation(self.io.set_kps, [id], [kp])

    def turn_on(self):
        self._safe_serial_operation(self.io.set_kps, list(self.joints.values()), self.low_torque_kps)
        print("turn on : low KPS set")
        time.sleep(1)

        self.set_position_all(self.init_pos)
        print("turn on : init pos set")

        time.sleep(1)

        self._safe_serial_operation(self.io.set_kps, list(self.joints.values()), self.kps)
        print("turn on : high kps")

    def turn_off(self):
        self._safe_serial_operation(self.io.disable_torque, list(self.joints.values()))

    def set_position(self, joint_name, pos):
        """
        pos is in radians
        """
        id = self.joints[joint_name]
        pos = pos + self.joints_offsets[joint_name]
        self._safe_serial_operation(self.io.write_goal_position, [id], [pos])

    def set_position_all(self, joints_positions):
        """
        joints_positions is a dictionary with joint names as keys and joint positions as values
        Warning: expects radians
        """
        ids_positions = {
            self.joints[joint]: position + self.joints_offsets[joint]
            for joint, position in joints_positions.items()
        }

        self._safe_serial_operation(
            self.io.write_goal_position,
            list(self.joints.values()), 
            list(ids_positions.values())
        )

    def get_present_positions(self, ignore=[]):
        """
        Returns the present positions in radians
        """
        result = self._safe_serial_operation(
            self.io.read_present_position,
            list(self.joints.values())
        )
        
        if result is None:
            # 返回缓存的数据或默认值
            if self.last_successful_positions is not None:
                print("Using cached position data due to communication error")
                return self.last_successful_positions
            else:
                print("No cached position data available, returning zeros")
                return np.zeros(len([j for j in self.joints.keys() if j not in ignore]))

        # 处理成功读取的数据
        present_positions = [
            pos - self.joints_offsets[joint]
            for joint, pos in zip(self.joints.keys(), result)
            if joint not in ignore
        ]
        
        result_array = np.array(np.around(present_positions, 3))
        self.last_successful_positions = result_array
        return result_array

    def get_present_velocities(self, rad_s=True, ignore=[]):
        """
        Returns the present velocities in rad/s (default) or rev/min
        """
        result = self._safe_serial_operation(
            self.io.read_present_velocity,
            list(self.joints.values())
        )
        
        if result is None:
            # 返回缓存的数据或默认值
            if self.last_successful_velocities is not None:
                print("Using cached velocity data due to communication error")
                return self.last_successful_velocities
            else:
                print("No cached velocity data available, returning zeros")
                return np.zeros(len([j for j in self.joints.keys() if j not in ignore]))

        # 处理成功读取的数据
        present_velocities = [
            vel
            for joint, vel in zip(self.joints.keys(), result)
            if joint not in ignore
        ]

        result_array = np.array(np.around(present_velocities, 3))
        self.last_successful_velocities = result_array
        return result_array
