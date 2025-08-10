import tempfile
import os
from vaulttool.utils import compute_checksum, encode_base64

def test_compute_checksum_and_base64():
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(b"vaulttool test data")
        tf.flush()
        checksum = compute_checksum(tf.name)
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # sha256
        with open(tf.name, "rb") as f:
            encoded = encode_base64(f.read())
        assert isinstance(encoded, bytes)
        assert encoded.startswith(b"dmF1bHR0b29sIHRlc3QgZGF0YQ==")
    os.unlink(tf.name)
