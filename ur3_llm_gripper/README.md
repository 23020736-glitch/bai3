# ur3_llm_gripper – LLM Skill Planning với Gripper và Camera (Bài 03)

Phát triển tiếp từ Bài 02, giữ kiến trúc **LLM → Plan → Robot Skills → MoveIt 2 → UR3e**, bổ sung:

- **Gripper thật** (2 ngón song song, điều khiển bằng *lực* + PID qua `gazebo_ros2_control`): vật được kẹp bằng ma sát,
  không dịch chuyển pose vật.
- **Camera trên cao** trong Gazebo + node `perception_node` nhận diện khối theo màu, đổi pixel → toạ độ bàn.
  Vị trí các khối **do camera quyết định**, các khối được đặt ngẫu nhiên mỗi lần chạy.
- **Kiểm tra vùng đích + xử lý vật cản** lúc thực thi: camera thấy vùng đích đang có vật khác → tự chèn
  `pick(vật cản)` → `move_to_temporary(vật cản)` rồi mới làm nhiệm vụ chính.

| | |
|---|---|
| **Họ tên** | (điền họ tên) |
| **MSSV** | 23020736 → P = 36 mod 6 = 0 → **A = Red, B = Yellow, C = Blue** |
| **Video** | (dán link) |

## Luồng xử lý

```
Lệnh tự nhiên ──► llm_planner ◄── /detect_objects (camera) ── perception_node ◄── ảnh Gazebo
                      │  prompt (config/prompt_template.txt) + trạng thái camera
                      ▼
                  LLM → JSON plan → Validator ──► /llm_plan
                                                      ▼
skill_executor:  insert_checks → [check_zone → camera → (chèn pick/move_to_temporary nếu bị chiếm)] → pick/place/home
                                                      ▼
                         robot_skills ──► MoveIt 2 (MoveGroup, Cartesian, PlanningScene) ──► UR3e + gripper
```

### Skills
`home`, `detect_objects`, `check_zone(zone)`, `pick(object)`, `place(object, zone)`, `move_to_temporary(object)`
(nội bộ: `find_free_position`, `open_gripper`, `close_gripper`). Trạng thái: `SUCCESS`, `FAILED`, `INVALID_OBJECT`,
`INVALID_ZONE`, `PLANNING_FAILED`, `NOT_FOUND` (camera không thấy vật), `GRASP_FAILED` (kẹp hụt, đo bằng độ rộng ngón tay),
`ZONE_OCCUPIED`, `NO_FREE_SPACE`.

## Cài đặt (Ubuntu 22.04, ROS 2 Humble)

```bash
sudo apt install -y git python3-colcon-common-extensions python3-rosdep python3-opencv python3-numpy \
  ros-humble-ur ros-humble-ur-moveit-config ros-humble-moveit ros-humble-gazebo-ros-pkgs \
  ros-humble-gazebo-ros2-control ros-humble-ros2-control ros-humble-ros2-controllers ros-humble-xacro
mkdir -p ~/ws3/src && cd ~/ws3/src
git clone -b humble https://github.com/UniversalRobots/Universal_Robots_ROS2_Gazebo_Simulation.git
git clone https://github.com/TEN_GITHUB/ur3-llm-gripper.git ur3_llm_gripper
cd ~/ws3 && source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build && source install/setup.bash
```
9Router + biến môi trường `NINEROUTER_BASE_URL / NINEROUTER_API_KEY / NINEROUTER_MODEL`: như Bài 02.

## Chạy

```bash
# Terminal 1
export PYTHONUNBUFFERED=1
ros2 launch ur3_llm_gripper llm_gripper.launch.py scenario:=blocked     # random | blocked | swap | line
# Terminal 2 (sau ~35 giây)
ros2 run ur3_llm_gripper llm_planner
```
Demo: `scenario:=blocked` (zone B có khối xanh) rồi gõ `Put the red cube in Zone B.` – robot tự gắp khối xanh ra
chỗ trống trước, rồi đặt khối đỏ vào B. Lệnh nâng cao: `Arrange all objects according to my student ID.`

Quan sát camera: `ros2 run rqt_image_view rqt_image_view` → topic `/perception/debug_image`.

## Cấu hình
`config/scene.yaml` (vị trí vùng, camera, màu HSV, gripper `close_d/hold_*`, `tcp_offset`), `config/ur3_controllers.yaml`
(PID gripper), `urdf/gripper.xacro` (gripper), `config/prompt_template.txt` (prompt).
