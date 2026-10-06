"""Node LLM Planner: lenh tu nhien + trang thai CAMERA -> LLM -> JSON plan -> validate -> /llm_plan."""
import json
import os
import threading
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import Trigger

from ur3_llm_gripper.llm_client import chat
from ur3_llm_gripper.task_validator import extract_json, load_config, student_targets, validate_plan

SKILL_DOC = """detect_objects()            - look at the table with the camera and update object states
check_zone(zone)            - use the camera to check whether a zone is free or occupied
pick(object)                - pick up an object with the gripper
place(object, zone)         - place the held object into a zone
move_to_temporary(object)   - put the held object into a free temporary spot found by the camera
home()                      - return the arm to the home pose"""


def describe_state(state):
    if not state:
        return "(camera not available)"
    lines = []
    for n, o in sorted(state["objects"].items()):
        where = "on the table" if o["location"] == "table" else f"in {o['location']}"
        lines.append(f"- {n}: {where} (x={o['x']:.2f}, y={o['y']:.2f})")
    for n in state.get("missing", []):
        lines.append(f"- {n}: not visible")
    return "\n".join(lines)


class LLMPlanner(Node):
    def __init__(self):
        super().__init__("llm_planner")
        scene, student = load_config()
        self.objects = [f"{c}_cube" for c in scene["colors"]]
        self.zones = list(scene["zones"])
        self.p, self.targets = student_targets(student["student_id"])
        self.student = student
        self.pub = self.create_publisher(String, "llm_plan", 10)
        self.cam = self.create_client(Trigger, "detect_objects")
        self.create_subscription(String, "execution_log", self.show_log, 10)

    def show_log(self, msg):
        print(msg.data, flush=True)
        if msg.data.strip().startswith("TASK"):
            print("> ", end="", flush=True)

    def camera_state(self):
        if not self.cam.wait_for_service(timeout_sec=2.0):
            return None
        fut = self.cam.call_async(Trigger.Request())
        t0 = time.time()
        while not fut.done() and time.time() - t0 < 6.0:
            time.sleep(0.05)
        if not fut.done() or not fut.result().success:
            return None
        return json.loads(fut.result().message)

    def system_prompt(self, state):
        from ament_index_python.packages import get_package_share_directory
        path = os.path.join(get_package_share_directory("ur3_llm_gripper"), "config", "prompt_template.txt")
        with open(path, encoding="utf-8") as f:
            t = f.read()
        mapping = "\n".join(f"{z} -> {o}" for z, o in self.targets.items())
        for k, v in {"SKILLS": SKILL_DOC, "OBJECTS": ", ".join(self.objects), "ZONES": ", ".join(self.zones),
                     "CAMERA": describe_state(state), "STUDENT_NAME": str(self.student["student_name"]),
                     "STUDENT_ID": str(self.student["student_id"]), "MAPPING": mapping}.items():
            t = t.replace(f"<<{k}>>", v)
        return t

    @staticmethod
    def fmt(s):
        args = [s[k] for k in ("object", "zone") if k in s]
        return f"{s['skill']}({', '.join(args)})"

    def handle_command(self, text):
        print(f"\nUSER COMMAND:\n{text}\n")
        state = self.camera_state()
        print("CAMERA:\n" + describe_state(state) + "\n")
        msgs = [{"role": "system", "content": self.system_prompt(state)}, {"role": "user", "content": text}]
        errs = []
        for _ in range(2):
            try:
                reply = chat(msgs)
            except Exception as e:
                print(f"LLM ERROR: {e}")
                return
            try:
                data = extract_json(reply)
            except ValueError as e:
                errs = [str(e)]
            else:
                if data.get("error") and not data.get("plan"):
                    print(f"LLM CANNOT PLAN: {data['error']}")
                    return
                errs = validate_plan(data, self.objects, self.zones)
                if not errs:
                    break
            msgs += [{"role": "assistant", "content": reply},
                     {"role": "user", "content": "Invalid plan: " + "; ".join(errs) +
                      ". Return a corrected JSON plan only."}]
        else:
            print("PLAN REJECTED (not executed):")
            for e in errs:
                print("  -", e)
            return
        print("LLM PLAN:")
        for s in data["plan"]:
            print("    " + self.fmt(s))
        self.pub.publish(String(data=json.dumps({"plan": data["plan"], "command": text})))


def main():
    rclpy.init()
    node = LLMPlanner()
    threading.Thread(target=rclpy.spin, args=(node,), daemon=True).start()
    print(f"Student {node.student['student_id']}: P={node.p}, target={node.targets}")
    print("Nhap lenh (Ctrl+D de thoat):")
    try:
        while True:
            cmd = input("> ").strip()
            if cmd:
                node.handle_command(cmd)
    except (EOFError, KeyboardInterrupt):
        pass
    rclpy.shutdown()
