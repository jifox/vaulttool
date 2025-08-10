import hashlib
import base64

def compute_checksum(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def encode_base64(data):
    return base64.b64encode(data)
