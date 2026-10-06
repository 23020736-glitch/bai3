# Bài 03

## 1. Yêu cầu

* Ubuntu 22.04
* ROS 2 Humble
* Gazebo Classic
* MoveIt 2
* Git
* Python 3
* Node.js >= 18
* 9Router

## 2. Clone project

```bash
mkdir -p ~/ws3/src
cd ~/ws3/src

git clone https://github.com/23020736-glitch/bai3.git ur3_llm_gripper

git clone -b humble \
https://github.com/UniversalRobots/Universal_Robots_ROS2_Gazebo_Simulation.git

git clone https://github.com/IFRA-Cranfield/IFRA_LinkAttacher.git
```

## 3. Cài package

```bash
sudo apt update

sudo apt install -y \
git \
python3-pip \
python3-colcon-common-extensions \
python3-rosdep \
ros-humble-moveit \
ros-humble-gazebo-ros-pkgs \
ros-humble-gazebo-ros2-control \
ros-humble-xacro
```

## 4. Cài dependency

```bash
cd ~/ws3

source /opt/ros/humble/setup.bash

sudo rosdep init 2>/dev/null || true
rosdep update

rosdep install \
--from-paths src \
--ignore-src \
-r -y
```

## 5. Build

```bash
cd ~/ws3

source /opt/ros/humble/setup.bash

colcon build --symlink-install

source ~/ws3/install/setup.bash
```

Kiểm tra:

```bash
ros2 pkg list | grep ur3_llm_gripper
```

## 6. 9Router

Khởi động 9Router trước.

API:

```text
http://localhost:20128/v1
```

Dashboard:

```text
http://localhost:20128/dashboard
```

Model:

```text
oc/muse-spark-1.3-contributor-free
```

Kiểm tra:

```bash
curl http://localhost:20128/v1/models
```

## 7. Chạy Bài 03

### Terminal 1

```bash
cd ~/ws3

source /opt/ros/humble/setup.bash
source ~/ws3/install/setup.bash

ros2 launch ur3_llm_gripper llm_gripper.launch.py scenario:=blocked
```

Chờ Gazebo + RViz chạy xong.

### Terminal 2

```bash
cd ~/ws3

source /opt/ros/humble/setup.bash
source ~/ws3/install/setup.bash

export PYTHONUNBUFFERED=1

ros2 run ur3_llm_gripper llm_planner
```

Nhập:

```text
Put the red cube in Zone B.
```

## 8. Kiểm tra camera

```bash
source /opt/ros/humble/setup.bash
source ~/ws3/install/setup.bash

ros2 topic list | grep -E "overhead|image"
```

```bash
ros2 topic info /overhead/cam/image_raw
```

## 9. Kiểm tra perception

```bash
ros2 service call /detect_objects std_srvs/srv/Trigger "{}"
```

## 10. Kiểm tra LinkAttacher

```bash
ros2 service list | grep ATTACHLINK
```

Cần có:

```text
/ATTACHLINK
/DETACHLINK
```

## 11. Nếu sửa code

```bash
cd ~/ws3

source /opt/ros/humble/setup.bash

colcon build --symlink-install \
--packages-select ur3_llm_gripper

source ~/ws3/install/setup.bash
```

## 12. Nếu Gazebo bị treo

```bash
pkill -9 gzserver 2>/dev/null || true
pkill -9 gzclient 2>/dev/null || true
pkill -9 rviz2 2>/dev/null || true
pkill -9 move_group 2>/dev/null || true
```

Chạy lại:

```bash
cd ~/ws3

source /opt/ros/humble/setup.bash
source ~/ws3/install/setup.bash

ros2 launch ur3_llm_gripper llm_gripper.launch.py scenario:=blocked
```
