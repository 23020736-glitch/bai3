"""Validator plan + cac ham xu ly ke hoach theo trang thai camera. Khong phu thuoc ROS."""
import json
import os
import re

import yaml

# skill -> tham so bat buoc
ALLOWED_SKILLS = {
    "home": [],
    "detect_objects": [],
    "check_zone": ["zone"],
    "pick": ["object"],
    "place": ["object", "zone"],
    "move_to_temporary": ["object"],
}

COLORS_BY_P = {
    0: ("red", "yellow", "blue"), 1: ("red", "blue", "yellow"),
    2: ("yellow", "red", "blue"), 3: ("yellow", "blue", "red"),
    4: ("blue", "red", "yellow"), 5: ("blue", "yellow", "red"),
}


def student_targets(student_id):
    p = int(str(student_id)[-2:]) % 6
    a, b, c = COLORS_BY_P[p]
    return p, {"zone_a": f"{a}_cube", "zone_b": f"{b}_cube", "zone_c": f"{c}_cube"}


def load_config(share_dir=None):
    if share_dir is None:
        from ament_index_python.packages import get_package_share_directory
        share_dir = get_package_share_directory("ur3_llm_gripper")
    with open(os.path.join(share_dir, "config", "scene.yaml")) as f:
        scene = yaml.safe_load(f)
    with open(os.path.join(share_dir, "config", "student_config.yaml")) as f:
        student = yaml.safe_load(f)
    return scene, student


def extract_json(text):
    t = re.sub(r"```(?:json)?", "", text)
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        raise ValueError("no JSON object in LLM reply")
    try:
        return json.loads(t[i:j + 1])
    except json.JSONDecodeError as e:
        raise ValueError(f"bad JSON: {e}")


def validate_plan(data, objects, zones):
    """Danh sach loi (rong = hop le): skill/object/zone/tham so + trang thai tay gap."""
    errs = []
    steps = data.get("plan") if isinstance(data, dict) else None
    if not isinstance(steps, list) or not steps:
        return ["'plan' must be a non-empty list"]
    held = None
    for i, s in enumerate(steps, 1):
        if not isinstance(s, dict) or s.get("skill") not in ALLOWED_SKILLS:
            errs.append(f"step {i}: skill not allowed: {s.get('skill') if isinstance(s, dict) else s}")
            continue
        for p in ALLOWED_SKILLS[s["skill"]]:
            if p not in s:
                errs.append(f"step {i}: {s['skill']} missing '{p}'")
        if "object" in s and s["object"] not in objects:
            errs.append(f"step {i}: unknown object '{s['object']}'")
        if "zone" in s and s["zone"] not in zones:
            errs.append(f"step {i}: unknown zone '{s['zone']}'")
        if s["skill"] == "pick":
            if held:
                errs.append(f"step {i}: pick while already holding {held}")
            held = s.get("object")
        elif s["skill"] in ("place", "move_to_temporary"):
            if held != s.get("object"):
                errs.append(f"step {i}: {s['skill']} {s.get('object')} but holding {held}")
            held = None
    return errs


# ---- xu ly ke hoach theo camera (chay luc thuc thi) ----
def insert_checks(steps, zones):
    """Truoc moi pick(obj) co place(obj, zone) phia sau -> chen check_zone(zone) (camera kiem tra vung dich)."""
    out = []
    for i, s in enumerate(steps):
        if s["skill"] == "pick":
            tz = next((t["zone"] for t in steps[i + 1:]
                       if t["skill"] == "place" and t["object"] == s["object"] and t["zone"] in zones), None)
            if tz and not (out and out[-1]["skill"] == "check_zone" and out[-1]["zone"] == tz):
                out.append({"skill": "check_zone", "zone": tz, "auto": True})
        out.append(s)
    return out


def blocker_steps(blocker):
    """Hanh dong phu khi camera thay vat can tro: gap vat do ra cho dat tam."""
    return [{"skill": "pick", "object": blocker, "auto": True},
            {"skill": "move_to_temporary", "object": blocker, "auto": True}]


def skip_task(queue, obj):
    """Vat da o dung vung dich -> bo pick(obj) va place(obj, ...) tuong ung trong hang doi."""
    q = list(queue)
    ip = next((i for i, s in enumerate(q) if s["skill"] == "pick" and s["object"] == obj), None)
    if ip is None:
        return q
    del q[ip]
    il = next((i for i, s in enumerate(q[ip:], ip) if s["skill"] == "place" and s["object"] == obj), None)
    if il is not None:
        del q[il]
    return q
