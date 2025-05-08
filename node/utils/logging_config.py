import logging

from utils.exception_decorator import log_exceptions


@log_exceptions
def setup_logging(node_id):
    logging.basicConfig(
        level=logging.INFO,
        format=f'[Node {node_id}] %(asctime)s %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )

