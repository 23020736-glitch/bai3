"""Tao URDF/xacro co gripper: chen gripper vao ur.urdf.xacro cai san (khong phu thuoc phien ban tham so)."""
import re


def make_wrapper(ur_xacro_text, gripper_xacro_path):
    arg = None
    for cand in ("tf_prefix", "prefix"):
        if re.search(r'<xacro:arg\s+name="%s"' % cand, ur_xacro_text):
            arg = cand
            break
    parent = f"$(arg {arg})tool0" if arg else "tool0"
    insert = (f'  <xacro:include filename="{gripper_xacro_path}"/>\n'
              f'  <xacro:ur3_gripper parent="{parent}"/>\n')
    i = ur_xacro_text.rfind("</robot>")
    if i < 0:
        raise ValueError("ur.urdf.xacro khong co </robot>")
    return ur_xacro_text[:i] + insert + ur_xacro_text[i:]
