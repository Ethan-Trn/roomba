import rclpy #ros client library everything ros related goes here
from rclpy.node import Node #node is a base class 
from std_msgs.msg import Int32 #the message type we're sending 

#inherits from node
class listener(Node):
    def __init__(self):
        super().__init__('listener') #creates a node called listener, node do method
        self.listen = self.create_subscription(Int32,'mf',self.alert,10)
       
    def alert(self,msg):
        self.get_logger().info(f'i see message {msg.data}')
        

def main(args = None):
    rclpy.init(args=args, domain_id=67) #tells code that this is realted to all things ros
    listen = listener()
    try:
        rclpy.spin(listen)
    except KeyboardInterrupt:
        pass
    finally:
        listen.destroy_node()
        rclpy.shutdown() #tells ros that this process no longer needs to connect to ros


if __name__ == '__main__':
    main()
