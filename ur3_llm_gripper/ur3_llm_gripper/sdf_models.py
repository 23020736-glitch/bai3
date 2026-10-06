"""Sinh SDF cho Gazebo: ban, vung, khoi (co khoi luong + ma sat that), camera tren cao."""
RGB = {"red": (1.0, 0.0, 0.0), "yellow": (1.0, 1.0, 0.0), "blue": (0.0, 0.0, 1.0),
    "green": (0.0, 1.0, 0.0),
    "purple": (0.6, 0.0, 0.8),
}
# vung/cho tam: mau NHAT (do bao hoa thap) de khong lan voi khoi khi loc mau HSV
PATCH_RGB = {"zone_a": (0.78, 0.9, 0.78), "zone_b": (0.95, 0.85, 0.72), "zone_c": (0.85, 0.78, 0.95)}
TEMP_RGB = (0.72, 0.72, 0.72)


def _mat(c):
    r, g, b = c
    return (f"<material><ambient>{r} {g} {b} 1</ambient><diffuse>{r} {g} {b} 1</diffuse>"
            f"<specular>0 0 0 1</specular></material>")


def cube_sdf(name, size, rgb, mass=0.05, mu=2.0):
    i = mass / 6.0 * size * size
    s = size
    return (f"<?xml version='1.0'?><sdf version='1.6'><model name='{name}'><link name='link'>"
            f"<inertial><mass>{mass}</mass><inertia><ixx>{i}</ixx><iyy>{i}</iyy><izz>{i}</izz>"
            f"<ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia></inertial>"
            f"<collision name='collision'><geometry><box><size>{s} {s} {s}</size></box></geometry>"
            f"<surface><friction><ode><mu>{mu}</mu><mu2>{mu}</mu2></ode></friction>"
            f"<contact><ode><kp>1000000</kp><kd>100</kd><min_depth>0.0005</min_depth><max_vel>0.1</max_vel>"
            f"</ode></contact></surface></collision>"
            f"<visual name='visual'><geometry><box><size>{s} {s} {s}</size></box></geometry>{_mat(rgb)}</visual>"
            f"</link></model></sdf>")


def table_sdf(top_z, size=1.2, thick=0.04):
    return (f"<?xml version='1.0'?><sdf version='1.6'><model name='table'><static>true</static><link name='link'>"
            f"<pose>0 0 {top_z - thick / 2}  0 0 0</pose>"
            f"<collision name='collision'><geometry><box><size>{size} {size} {thick}</size></box></geometry>"
            f"<surface><friction><ode><mu>1.0</mu><mu2>1.0</mu2></ode></friction></surface></collision>"
            f"<visual name='visual'><geometry><box><size>{size} {size} {thick}</size></box></geometry>"
            f"{_mat((0.45, 0.40, 0.35))}</visual></link></model></sdf>")


def patch_sdf(name, rgb, side=0.08, thick=0.002):
    return (f"<?xml version='1.0'?><sdf version='1.6'><model name='{name}'><static>true</static><link name='link'>"
            f"<visual name='visual'><geometry><box><size>{side} {side} {thick}</size></box></geometry>{_mat(rgb)}"
            f"</visual></link></model></sdf>")


def camera_sdf(cam):
    return (f"<?xml version='1.0'?><sdf version='1.6'><model name='overhead_camera'><static>true</static>"
            f"<link name='link'><sensor name='cam' type='camera'><always_on>true</always_on>"
            f"<update_rate>10</update_rate><visualize>false</visualize>"
            f"<camera><horizontal_fov>{cam['hfov']}</horizontal_fov>"
            f"<image><width>{cam['width']}</width><height>{cam['height']}</height><format>R8G8B8</format></image>"
            f"<clip><near>0.05</near><far>5</far></clip></camera>"
            f"<plugin name='camera_controller' filename='libgazebo_ros_camera.so'>"
            f"<ros><namespace>/overhead</namespace></ros><camera_name>cam</camera_name>"
            f"<frame_name>overhead_camera_link</frame_name></plugin></sensor></link></model></sdf>")
