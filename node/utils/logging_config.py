import logging

def setup_logging(node_id):
    logging.basicConfig(
        level=logging.INFO,
        format=f'[Node {node_id}] %(asctime)s %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )

