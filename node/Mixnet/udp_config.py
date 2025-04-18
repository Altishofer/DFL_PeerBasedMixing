from dataclasses import dataclass

# heyo

@dataclass(frozen=True)
class UdpConfig:
    MAX_UDP_PAYLOAD: int = 1400
    SLEEP_BETWEEN_MSG: float = 0.0002 # 0.0005
    SEND_WINDOW_SIZE: int = 64
    SLEEP_MIX_DELAY: float = 0.2

    MIN_WAIT_RESEND: float = 0
    MAX_WAIT_RESEND: float = 10
    RESEND_RTT_FACTOR: float = 3 # 2.5

    MIN_WAIT_ACK: float = 0
    MAX_WAIT_ACK: float = 10
    ACK_RTT_FACTOR: float = 0.5

    WAIT_WINDOW_FULL: float = 0.01

    INITIAL_RTT = 5

    N_HOPS: int = 2
