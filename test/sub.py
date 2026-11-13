import rclpy #ros client library everything ros related goes here
from rclpy.node import Node #node is a base class 
from std_msgs.msg import Int32 #the message type we're sending 

#inherits from node
class listener(Node):
    def __init__(self):
        super().__init__('listener') #creates a node called listener, node do method
        self.listen = self.create_subscription(Int32,'mf'.alert(),10)
       
    def alert(self,msg):
        self.get_logger().info('i see message {msg}')
        

    def main(args = None):
        rclpy.init(args = args) #tells code that this is realted to all things ros
        listener = listener()
        try:
            rclpy.spin(listener)
        except KeyboardInterrupt:
            pass
        finally:
            listener.destroy_node()
            rclpy.shutdown() #tells ros that this process no longer needs to connect to ros
        

