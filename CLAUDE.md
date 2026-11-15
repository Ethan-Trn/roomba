# roomba

ROS 2 (distro `lyrical`) colcon workspace. Package: `src/roomba` (ament_python).

## Architecture

- **Pi 3B+** only gathers sensor data and publishes it. No drawing, no heavy compute.
- **Laptop** subscribes and does the heavy work (RViz now, mapping later).
- Both use `domain_id=67` (set in code via `rclpy.init(domain_id=67)`). Keep them the same.

## LD06 lidar

- `roomba/ld06.py`: protocol only (CRC-8, packet decode, resync parser, scan assembler). No ROS, no serial.
- `roomba/sources.py`: `LidarSource` base class (`open`/`read`/`close`). `UartSource`, `UsbSource`
  (via `SerialSource`) and `SimulatedSource` override how bytes arrive. Add new transports here.
- `roomba/lidar_node.py`: node `ld06`, publishes `sensor_msgs/LaserScan` on `/scan`, frame `lidar`.
- Run: `ros2 run roomba lidar --ros-args -p source:=uart|usb|sim [-p port:=/dev/ttyUSB0]`
- Protocol: 230400 8N1, 47-byte packets (`0x54 0x2C` ... crc8), 12 points each, angles in 0.01 deg,
  CRC-8 poly 0x4D init 0 over bytes 0..45. Sensor angles are clockwise; ROS output is counter-clockwise.
- Tests (no ROS or hardware needed): `python3 -m pytest src/roomba/test/test_ld06.py`

## Pi setup for the GPIO UART

- Lidar TX -> Pi RX (GPIO15, pin 10). Lidar needs 5 V; its TX is 3.3 V logic. Motor spins on power, no PWM needed.
- In `/boot/firmware/config.txt`: `enable_uart=1` and `dtoverlay=disable-bt` (gives the reliable PL011 UART
  on `/dev/serial0`; the mini UART can drop bytes at 230400). Also disable the `hciuart` service. Reboot.
- Add user to `dialout`. Install `python3-serial`.
- Quick hardware check: `cat /dev/serial0 | xxd | head` should show `54 2c` about every 47 bytes
  (set the port first with `stty -F /dev/serial0 230400 raw`).

## RViz on the laptop

`rviz2`, set Fixed Frame to `lidar`, add a LaserScan display on `/scan`. Run with `ROS_DOMAIN_ID=67`.

## Build

See HELPME.md. In short: `colcon build --packages-select roomba --symlink-install`, then source `install/setup.bash`.
Never edit `build/`, `install/`, `log/`.
