import rclpy #ros client library everything ros related goes here
from rclpy.node import Node #node is a base class 
from std_msgs.msg import Int32 #the message type we're sending 

#inherits from node
class Talker(Node):
    def __init__(self):
        super().__init__('talker') #creates a node called talker, node do method
        self.pub = self.create_publisher(Int32, 'mf', 10) #creates the publisher
        self.message_id = 0 #each message should have an id 
        self.timer = self.create_timer(.5,self.alert) #everytime this 

    def alert(self):
        msg = Int32()
        msg.data = self.message_id
        self.pub.publish(msg)
        self.message_id += 1

    def main(args = None):
        rclpy.init(args = args) #tells code that this is realted to all things ros
        talker = Talker()
        try:
            rclpy.spin(talker)
        except KeyboardInterrupt:
            pass
        finally:
            talker.destroy_node()
            rclpy.shutdown() #tells ros that this process no longer needs to connect to ros
    if __name__ == '__main__':
            main()
        

