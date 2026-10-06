"""Node camera: nhan anh tu Gazebo, nhan dien khoi theo mau, cung cap service /detect_objects (Trigger, JSON)."""
import json
import time

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_srvs.srv import Trigger

from ur3_llm_gripper.task_validator import load_config
from ur3_llm_gripper.vision import OverheadCamera, build_state, detect_cubes


class Perception(Node):
    def __init__(self):
        super().__init__("perception")
        self.scene, _ = load_config()
        self.cam = OverheadCamera(self.scene["camera"])
        self.img, self.img_t = None, 0.0
        self.create_subscription(Image, self.scene["camera"]["topic"], self.on_image, qos_profile_sensor_data)
        self.create_service(Trigger, "detect_objects", self.on_detect)
        self.dbg = self.create_publisher(Image, "perception/debug_image", 1)
        self.create_timer(1.0, self.on_timer)
        self.last_state = None
        self.get_logger().info("perception san sang, doi anh tu " + self.scene["camera"]["topic"])

    def on_image(self, msg):
        arr = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.step)[:, :msg.width * 3]
        img = arr.reshape(msg.height, msg.width, 3)
        self.img = img[:, :, ::-1].copy() if msg.encoding == "rgb8" else img.copy()   # -> BGR
        self.img_t = time.time()

    def detect(self):
        dets = detect_cubes(self.img, self.cam, self.scene)
        return build_state(dets, self.scene), dets

    def on_detect(self, req, res):
        if self.img is None or time.time() - self.img_t > 3.0:
            res.success, res.message = False, "khong co anh camera moi"
            return res
        state, _ = self.detect()
        self.last_state = state
        res.success, res.message = True, json.dumps(state)
        return res

    def on_timer(self):
        if self.img is None:
            return
        state, dets = self.detect()
        vis = self.img.copy()
        for d in dets:
            u, v = int(d["px"][0]), int(d["px"][1])
            cv2.circle(vis, (u, v), 6, (255, 255, 255), 2)
            loc = state["objects"][d["name"]]["location"]
            cv2.putText(vis, f"{d['name']} {loc}", (u + 8, v), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        m = Image()
        m.height, m.width, m.encoding, m.step = vis.shape[0], vis.shape[1], "bgr8", vis.shape[1] * 3
        m.data = vis.tobytes()
        self.dbg.publish(m)


def main():
    rclpy.init()
    rclpy.spin(Perception())
    rclpy.shutdown()
