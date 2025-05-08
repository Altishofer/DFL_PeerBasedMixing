from utils.exception_decorator import log_exceptions


class MsgCache:

    def __init__(self):
        self._surb_key_store = {}

    @log_exceptions
    def new_fragment(self, surb_id, surb_key_tuple):
        self._surb_key_store[surb_id] = surb_key_tuple

    @log_exceptions
    def received_surb(self, surb_id):
        surb_key_tuple = self._surb_key_store[surb_id]
        del self._surb_key_store[surb_id]
        return surb_key_tuple