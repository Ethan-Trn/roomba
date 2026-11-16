"""ROS 2 node: read an LD06 from a source and publish sensor_msgs/LaserScan.

Runs on the Pi. The laptop only subscribes (RViz). Same domain id as topic.py / sub.py.
"""
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan

from roomba.lidar.ld06 import PacketParser, ScanAssembler
from roomba.lidar.sources import SimulatedSource, UartSource, UsbSource

DOMAIN_ID = 67  # must match the laptop
SOURCES = {'uart': UartSource, 'usb': UsbSource}

#essetialy what it does is that it creates the full turn and seds that as a packet to the topic and also every 5 seconds it gives a summary of what's happenig

class LidarNode(Node):
    """Publishes one LaserScan per lidar turn (about 10 per second)."""

    def __init__(self):
        super().__init__('ld06')
        #the reason why they do declare_parameter is so that way 
        self.declare_parameter('source', 'uart')  # uart | usb | sim
        self.declare_parameter('port', '')        # for the port later on when we connect this to a usb
        self.declare_parameter('body_frame', 'lidar') #naming the body frame
        self.declare_parameter('topic', 'scan') #name of the publisher

        kind = self.get_parameter('source').value
        port = self.get_parameter('port').value
        if kind == 'sim':
            self.source = SimulatedSource()
        elif kind in SOURCES:
            self.source = SOURCES[kind](port or None)
        else:
            raise ValueError(f"source must be uart, usb or sim, got '{kind}'")
        self.source.open()
        self.get_logger().info(f'lidar source: {kind}')

        self.frame_id = self.get_parameter('body_frame').value
        self.parser = PacketParser()
        self.assembler = ScanAssembler()
        self.pub = self.create_publisher(LaserScan, self.get_parameter('topic').value, 5)

        self._last_scan_t = None
        self._scans = 0
        self._report_t = time.monotonic()
        self.create_timer(0.005, self._alert)

    def _alert(self):
        for pkt in self.parser.feed(self.source.read()): #for each packet that has been collected every 5 mili seconds
            scan = self.assembler.add(pkt) #basically what it does is it adds all the poits and checks to
            if scan is not None: #publish it when full circle
                self._publish(scan)
        self._summary() 
        
            

    def _publish(self, scan):
        now = time.monotonic()
        period = 0.1 if self._last_scan_t is None else now - self._last_scan_t
        self._last_scan_t = now
        n = len(scan.ranges)

        msg = LaserScan()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        msg.angle_min = scan.angle_min
        msg.angle_increment = scan.angle_increment
        msg.angle_max = scan.angle_max
        msg.scan_time = period
        msg.time_increment = period / n
        msg.range_min = scan.range_min
        msg.range_max = scan.range_max
        msg.ranges = scan.ranges
        self.pub.publish(msg)
        self._scans += 1

    def _summary(self):
        now = time.monotonic()
        if now - self._report_t < 5.0:
            return
        rate = self._scans / (now - self._report_t)
        self.get_logger().info(
            f'{rate:.1f} scans/s, packets ok={self.parser.good} bad_crc={self.parser.bad}')
        self._scans = 0
        self._report_t = now

    def destroy_node(self):
        self.source.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args, domain_id=DOMAIN_ID)
    node = LidarNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
