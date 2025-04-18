

class ServerStats:

    def __init__(self):
        self.total_fragments = 0
        self.total_bytes = 0
        self.total_sequences = 0
        self.lost_fragments = 0
        self.ack_messages = 0
        self.total_real_time = 0
        self.max_link_speed = 0
        self.rtt = 0
        self.not_acked = 0
        self.mix_forward = 0

    def forwarded_message(self):
        self.mix_forward += 1
