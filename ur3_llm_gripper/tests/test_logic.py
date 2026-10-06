import math, os, sys, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2, numpy as np, yaml
from ur3_llm_gripper.vision import *
from ur3_llm_gripper.layout import initial_layout
from ur3_llm_gripper.task_validator import *
from ur3_llm_gripper.description import make_wrapper

scene = yaml.safe_load(open("config/scene.yaml"))
cam = OverheadCamera(scene["camera"])

# 1) camera: pixel <-> world
for p in [(-0.40, 0.12, 0.0), (-0.25, -0.15, 0.0), (-0.18, 0.27, 0.0)]:
    u, v = cam.world_to_pixel(p)
    q = cam.pixel_to_world(u, v, p[2])
    assert np.allclose(q, p, atol=1e-9), (p, q)
# huong anh: x tang -> v giam (len), y tang -> u giam (sang trai)
u0, v0 = cam.world_to_pixel((-0.3, 0, 0)); u1, v1 = cam.world_to_pixel((-0.2, 0, 0)); u2, v2 = cam.world_to_pixel((-0.3, 0.1, 0))
assert v1 < v0 and u2 < u0
print("camera model OK")

# 2) ve anh gia lap (ca mat ben) va nhan dien lai
HSV_BGR = {"red": (0, 0, 255), "yellow": (0, 255, 255), "blue": (255, 0, 0)}
def render(positions):
    img = np.full((480, 640, 3), (90, 110, 130), np.uint8)       # mau ban
    for name, (zx, zy) in all_places(scene).items():              # vung nhat mau
        c = [cam.world_to_pixel((zx + dx, zy + dy, scene["table_top_z"])) for dx in (-.04, .04) for dy in (-.04, .04)]
        cv2.fillConvexPoly(img, cv2.convexHull(np.array(c, np.float32)).astype(np.int32), (200, 215, 205))
    s2, tt = scene["cube_size"] / 2, scene["table_top_z"]
    for name, (x, y) in positions.items():
        col = HSV_BGR[name.split("_")[0]]
        pts = [cam.world_to_pixel((x + a, y + b, tt + h)) for a in (-s2, s2) for b in (-s2, s2) for h in (0, 2 * s2)]
        cv2.fillConvexPoly(img, cv2.convexHull(np.array(pts, np.float32)).astype(np.int32), col)
    return img

worst = 0
for seed in range(40):
    lay = initial_layout("random", scene, seed)
    dets = detect_cubes(render(lay), cam, scene)
    assert len(dets) == 3, (seed, dets)
    for d in dets:
        ex, ey = lay[d["name"]]
        worst = max(worst, math.hypot(d["x"] - ex, d["y"] - ey))
print(f"detection sai so lon nhat qua 40 bo tri ngau nhien: {worst*1000:.1f} mm")
assert worst < 0.008

# 3) camera thay vat trong vung -> trang thai
for sc in ("blocked", "swap"):
    lay = initial_layout(sc, scene, 1)
    st = build_state(detect_cubes(render(lay), cam, scene), scene)
    print(sc, {n: o["location"] for n, o in st["objects"].items()})
st = build_state(detect_cubes(render(initial_layout("blocked", scene, 1)), cam, scene), scene)
assert zone_occupant(st, "zone_b") == "blue_cube" and zone_occupant(st, "zone_b", exclude="blue_cube") is None
assert free_temp_slot(st, scene) == "temp_1"
# khoi nam gan temp_1 -> chon temp_2
st2 = {"objects": {"red_cube": {"x": -0.30, "y": 0.27, "yaw": 0, "location": "temp_1"}}}
assert free_temp_slot(st2, scene) == "temp_2"

# 4) bat gap yeu: khoi bi che -> missing
img = render(initial_layout("random", scene, 3)); img[:] = (90, 110, 130)
assert len(build_state(detect_cubes(img, cam, scene), scene)["missing"]) == 3

# 5) validator + xu ly ke hoach theo camera
objs = ["red_cube", "yellow_cube", "blue_cube"]; zones = ["zone_a", "zone_b", "zone_c"]
plan = {"plan": [{"skill": "pick", "object": "red_cube"}, {"skill": "place", "object": "red_cube", "zone": "zone_b"}, {"skill": "home"}]}
assert validate_plan(plan, objs, zones) == []
bad = {"plan": [{"skill": "move_joint"}, {"skill": "pick", "object": "green_cube"}, {"skill": "place", "object": "red_cube", "zone": "zone_z"}]}
print("validator tu choi:", validate_plan(bad, objs, zones))
assert len(validate_plan(bad, objs, zones)) >= 3
q = insert_checks(plan["plan"], zones)
assert [s["skill"] for s in q] == ["check_zone", "pick", "place", "home"]
# camera bao zone_b co blue_cube -> chen hanh dong phu truoc pick(red)
queue = q[1:]; queue[0:0] = blocker_steps("blue_cube")
print("hang doi sau khi camera thay vat can tro:", [f"{s['skill']}({s.get('object', '')})" for s in queue])
assert [s["skill"] for s in queue] == ["pick", "move_to_temporary", "pick", "place", "home"]
assert validate_plan({"plan": queue}, objs, zones) == []
# vat da o dung vung -> bo
q2 = skip_task(q[1:], "red_cube"); assert [s["skill"] for s in q2] == ["home"]

# 6) bo tri ban dau hop le & xacro
for sc in ("random", "blocked", "swap", "line"):
    lay = initial_layout(sc, scene, 7); assert len(lay) == 3
ur = '<robot name="ur"><xacro:arg name="tf_prefix" default=""/><link name="tool0"/></robot>'
w = make_wrapper(ur, os.path.abspath("urdf/gripper.xacro"))
assert 'parent="$(arg tf_prefix)tool0"' in w and w.rstrip().endswith("</robot>")
open("/tmp/wrap_test.xacro", "w").write(w)
print("ALL TESTS OK")
