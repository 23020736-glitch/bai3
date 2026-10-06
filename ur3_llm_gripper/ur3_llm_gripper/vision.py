"""Camera tren cao -> vi tri cac khoi. Thuan numpy/OpenCV, khong phu thuoc ROS (test duoc doc lap)."""
import math

import cv2
import numpy as np


def rpy_to_matrix(r, p, y):
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return rz @ ry @ rx


class OverheadCamera:
    """Pinhole. He toa do camera cua Gazebo: x phia truoc, y trai, z len; anh: u sang phai, v xuong."""

    def __init__(self, cfg):
        self.w, self.h = cfg["width"], cfg["height"]
        self.f = (self.w / 2.0) / math.tan(cfg["hfov"] / 2.0)
        self.cx, self.cy = self.w / 2.0, self.h / 2.0
        self.pos = np.array([cfg["x"], cfg["y"], cfg["z"]], dtype=float)
        self.rot = rpy_to_matrix(cfg["roll"], cfg["pitch"], cfg["yaw"])

    def pixel_to_world(self, u, v, z):
        d = self.rot @ np.array([1.0, -(u - self.cx) / self.f, -(v - self.cy) / self.f])
        t = (z - self.pos[2]) / d[2]
        return self.pos + t * d

    def world_to_pixel(self, p):
        d = self.rot.T @ (np.asarray(p, dtype=float) - self.pos)
        return self.cx - self.f * d[1] / d[0], self.cy - self.f * d[2] / d[0]


def _wrap_quarter(a):
    return (a + math.pi / 4) % (math.pi / 2) - math.pi / 4


def detect_cubes(bgr, cam, scene):
    """Tra ve [{name, x, y, yaw, area}] cho moi mau khoi thay duoc (khoi lon nhat moi mau)."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    size = scene["cube_size"]
    z_mid = scene["table_top_z"] + size / 2.0   # mat phang qua tam khoi: giam lech do mat ben
    min_area = scene.get("perception", {}).get("min_area", 120)
    out = []
    for color, ranges in scene["colors"].items():
        mask = np.zeros(hsv.shape[:2], np.uint8)
        for r in ranges:
            mask |= cv2.inRange(hsv, np.array(r[:3], np.uint8), np.array(r[3:], np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = [c for c in cnts if cv2.contourArea(c) >= min_area]
        if not cnts:
            continue
        c = max(cnts, key=cv2.contourArea)
        m = cv2.moments(c)
        u, v = m["m10"] / m["m00"], m["m01"] / m["m00"]
        x, y, _ = cam.pixel_to_world(u, v, z_mid)
        box = cv2.boxPoints(cv2.minAreaRect(c))
        p0, p1 = cam.pixel_to_world(*box[0], z_mid), cam.pixel_to_world(*box[1], z_mid)
        yaw = _wrap_quarter(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
        out.append({"name": f"{color}_cube", "x": float(x), "y": float(y), "yaw": float(yaw),
                    "area": float(cv2.contourArea(c)), "px": [float(u), float(v)]})
    return out


def all_places(scene):
    return {**scene["zones"], **scene["temp_positions"]}


def locate(x, y, scene):
    half = scene["zone_size"] / 2.0 + scene.get("zone_tol", 0.012)
    for name, (zx, zy) in all_places(scene).items():
        if abs(x - zx) <= half and abs(y - zy) <= half:
            return name
    return "table"


def build_state(dets, scene):
    objs = {d["name"]: {"x": round(d["x"], 4), "y": round(d["y"], 4), "yaw": round(d["yaw"], 4),
                        "location": locate(d["x"], d["y"], scene)} for d in dets}
    expected = [f"{c}_cube" for c in scene["colors"]]
    return {"objects": objs, "missing": [n for n in expected if n not in objs]}


def zone_occupant(state, zone, exclude=None):
    for n, o in state.get("objects", {}).items():
        if o["location"] == zone and n != exclude:
            return n
    return None


def free_temp_slot(state, scene, exclude=None, min_clear=0.07):
    """Cho dat tam dau tien ma camera khong thay khoi nao nam gan."""
    for name, (sx, sy) in scene["temp_positions"].items():
        ok = True
        for n, o in state.get("objects", {}).items():
            if n != exclude and max(abs(o["x"] - sx), abs(o["y"] - sy)) < min_clear:
                ok = False
                break
        if ok:
            return name
    return None
