import logging
import pickle
from collections import defaultdict

from utils.exception_decorator import log_exceptions


class MessageManager:
    def __init__(self, node_id, total_peers, transport, model_handler):
        self._node_id = node_id
        self._total_peers = total_peers
        self._transport = transport
        self._model_handler = model_handler
        self._incoming_parts = defaultdict(lambda: defaultdict(dict))
        self._model_buffer = defaultdict(list)

    @log_exceptions
    async def send_model(self, current_round):
        model_data = self._model_handler.serialize_model()
        chunks = self._model_handler.chunk(model_data, 600)

        for peer_id in range(self._total_peers):
            if peer_id == self._node_id:
                continue
            for idx, chunk in enumerate(chunks):
                msg = {
                    "type": "model_part",
                    "round": current_round,
                    "sender": self._node_id,
                    "part_idx": idx,
                    "total_parts": len(chunks),
                    "data": chunk
                }
                await self._transport.send(msg, peer_id)

        logging.info(f"Sent model in {len(chunks)} parts each")

    @log_exceptions
    async def collect_models(self, current_round, own_model):
        self._model_buffer[current_round].append(own_model)

        while len(self._model_buffer[current_round]) < self._total_peers:
            msg = await self._transport.receive()
            parsed = pickle.loads(msg)

            if parsed["type"] == "model_part":
                sender = parsed["sender"]
                part_idx = parsed["part_idx"]
                total_parts = parsed["total_parts"]
                msg_round = parsed["round"]
                self._incoming_parts[msg_round][sender][part_idx] = parsed["data"]

                current_parts = self._incoming_parts[msg_round][sender]
                logging.debug(f"Received part {part_idx+1}/{total_parts} from Node {sender} for round {msg_round}")

                if len(current_parts) == total_parts and set(current_parts.keys()) == set(range(total_parts)):
                    full_data = b"".join(current_parts[i] for i in range(total_parts))
                    model = self._model_handler.deserialize_model(full_data)
                    self._model_buffer[msg_round].append(model)
                    logging.info(f"Reassembled full model from Node {sender} for round {msg_round}")

        return self._model_buffer[current_round]
