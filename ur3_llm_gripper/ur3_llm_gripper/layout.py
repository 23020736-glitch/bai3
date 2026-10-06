"""Bo tri ban dau cua cac khoi trong mo phong (de camera phai tu nhan biet, khong dung vi tri khai bao san)."""
import random


def initial_layout(scenario, scene, seed=None):
    rng = random.Random(seed)
    names = [f"{c}_cube" for c in scene["colors"]]
    a = scene["spawn_area"]
    zones = scene["zones"]
    fixed = {}
    if scenario == "blocked":            # vung B dang co khoi xanh -> robot phai don truoc
        fixed["blue_cube"] = tuple(zones["zone_b"])
    elif scenario == "swap":             # vang o A, do o B
        fixed["yellow_cube"] = tuple(zones["zone_a"])
        fixed["red_cube"] = tuple(zones["zone_b"])
    elif scenario == "line":             # 3 khoi thang hang, co dinh
        return {n: (-0.40, y) for n, y in zip(names, (-0.12, 0.0, 0.12))}
    elif scenario != "random":
        raise ValueError(f"scenario khong hop le: {scenario}")
    for _ in range(300):                  # thu lai ca bo tri neu ket (cac khoi dau chiem het cho)
        out = dict(fixed)
        ok = True
        for n in names:
            if n in out:
                continue
            for _ in range(100):
                p = (rng.uniform(a["x_min"], a["x_max"]), rng.uniform(a["y_min"], a["y_max"]))
                if all(max(abs(p[0] - q[0]), abs(p[1] - q[1])) >= a["min_sep"] for q in out.values()):
                    out[n] = p
                    break
            else:
                ok = False
                break
        if ok:
            return out
    raise RuntimeError("khong dat duoc khoi (min_sep qua lon)")
