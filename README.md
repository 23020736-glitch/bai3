# Bài thực hành 03 – LLM Skill Planning với Gripper và Camera

Hệ thống robot UR3e mô phỏng sử dụng:

* ROS 2 Humble
* Ubuntu 22.04
* Gazebo Classic
* MoveIt 2
* UR3e
* Gripper
* Camera overhead
* LLM Planner
* 9Router
* IFRA LinkAttacher

## 1. Kiến trúc hệ thống

```text
Natural Language Command
          |
          v
      LLM Planner
          |
          v
    Structured Plan
          |
          v
     Plan Validator
          |
          v
     Skill Executor
       /       \
      /         \
 Camera        Robot Skills
   |               |
   v               v
Perception       MoveIt 2
                   |
                   v
             UR3e + Gripper
                   |
                   v
                Gazebo
```

LLM chỉ có nhiệm vụ:

1. Hiểu câu lệnh người dùng.
2. Chọn skill.
3. Xác định tham số.
4. Sắp xếp thứ tự skill.

LLM **không điều khiển trực tiếp joint** và không sinh joint trajectory.

---

# 2. Yêu cầu hệ thống

Máy mới cần:

* Ubuntu 22.04
* ROS 2 Humble
* Gazebo Classic
* MoveIt 2
* Git
* Python 3
* Node.js >= 18 nếu cần sử dụng các thành phần 9Router/LLM tương ứng.

Kiểm tra ROS:

```bash
source /opt/ros/humble/setup.bash

ros2 --version
gazebo --version
```

---

# 3. Tạo workspace

```bash
mkdir -p ~/ws3/src
cd ~/ws3/src
```

Clone repository chính:

```bash
git clone https://github.com/23020736-glitch/ur3-llm-gripper-bai03.git ur3_llm_gripper
```

Repository cần thiết cho UR3:

```bash
git clone -b humble https://github.com/UniversalRobots/Universal_Robots_ROS2_Gazebo_Simulation.git
```

Đổi tên/thư mục nếu cần để đúng cấu trúc:

```text
~/ws3/src/
├── ur3_llm_gripper/
├── Universal_Robots_ROS2_Gazebo_Simulation/
└── IFRA_LinkAttacher/
```

---

# 4. IFRA LinkAttacher

Project sử dụng IFRA LinkAttacher để mô phỏng việc gripper giữ block trong Gazebo.

Clone:

```bash
cd ~/ws3/src

git clone https://github.com/IFRA-Cranfield/IFRA_LinkAttacher.git
```

Nếu repository đã được đưa vào project dưới dạng submodule, có thể dùng:

```bash
cd ~/ws3
git submodule update --init --recursive
```

---

# 5. Cài dependency

Quay về workspace:

```bash
cd ~/ws3

source /opt/ros/humble/setup.bash

rosdep update

rosdep install \
  --from-paths src \
  --ignore-src \
  -r -y
```

Nếu một package đã được cài sẵn thì rosdep có thể báo package đó đã được đáp ứng.

---

# 6. Build

Build toàn bộ workspace:

```bash
cd ~/ws3

source /opt/ros/humble/setup.bash

colcon build --symlink-install
```

Sau khi build:

```bash
source ~/ws3/install/setup.bash
```

Kiểm tra package:

```bash
ros2 pkg list | grep ur3_llm_gripper
```

Kết quả cần có:

```text
ur3_llm_gripper
```

---

# 7. Cấu hình LLM / 9Router

Project sử dụng LLM thông qua 9Router.

Base URL:

```text
http://localhost:20128/v1
```

Dashboard:

```text
http://localhost:20128/dashboard
```

Model sử dụng trong project:

```text
oc/muse-spark-1.3-contributor-free
```

Đảm bảo 9Router đang chạy trước khi chạy LLM Plan
