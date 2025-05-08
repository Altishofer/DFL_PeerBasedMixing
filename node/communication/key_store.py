import pickle

from petlib.bn import Bn
from petlib.ec import EcGroup, EcPt

from sphinxmix.SphinxClient import (
    pki_entry
)

from utils.exception_decorator import log_exceptions


class KeyStore:

    def __init__(self):
        self._pkiPriv = dict()
        self._pkiPub = dict()
        self.load_keys()

    @log_exceptions
    def load_keys(self):

        priv_path = "/config/pki_priv.pkl"
        pub_path = "/config/pki_pub.pkl"

        with open(priv_path, "rb") as f:
            priv_raw = pickle.load(f)

        with open(pub_path, "rb") as f:
            pub_raw = pickle.load(f)

        ec = EcGroup()
        self._pkiPriv = {}
        self._pkiPub = {}

        for nid, x_bytes, y_bytes in priv_raw.values():
            x = Bn.from_binary(x_bytes)
            y = EcPt.from_binary(y_bytes, ec)
            self._pkiPriv[nid] = pki_entry(nid, x, y)

        for nid, y_bytes in pub_raw.values():
            y = EcPt.from_binary(y_bytes, ec)
            self._pkiPub[nid] = pki_entry(nid, None, y)

    @log_exceptions
    def get_x(self, node_id):
        if node_id in self._pkiPriv:
            return self._pkiPriv[node_id].x
        return None

    @log_exceptions
    def get_y(self, node_id):
        if node_id in self._pkiPub:
            return self._pkiPriv[node_id].y
        return None

