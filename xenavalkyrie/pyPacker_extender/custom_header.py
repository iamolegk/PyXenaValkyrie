from pypacker import pypacker


class custom(pypacker.Packet):
    def __init__(self,body_bytes):
        super(custom, self).__init__(body_bytes)

    def _dissect(self,data):
        return len(data)