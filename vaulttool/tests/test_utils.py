import tempfile
import os
from vaulttool.utils import compute_checksum, encode_base64, compute_hmac, derive_keys

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


def test_derive_keys():
    """Test HKDF key derivation produces two different keys."""
    with tempfile.NamedTemporaryFile(delete=False, mode='wb') as kf:
        kf.write(b"test_master_key_for_derivation_1234567890")
        kf.flush()
        key_file = kf.name
    
    try:
        hmac_key, encryption_key = derive_keys(key_file)
        
        # Check both keys are 32 bytes
        assert len(hmac_key) == 32
        assert len(encryption_key) == 32
        
        # Check keys are different (cryptographically separated)
        assert hmac_key != encryption_key
        
        # Check keys are deterministic (same input = same output)
        hmac_key2, encryption_key2 = derive_keys(key_file)
        assert hmac_key == hmac_key2
        assert encryption_key == encryption_key2
        
    finally:
        os.unlink(key_file)


def test_compute_hmac():
    """Test HMAC computation."""
    with tempfile.NamedTemporaryFile(delete=False, mode='w') as tf:
        tf.write("test data for HMAC computation")
        tf.flush()
        test_file = tf.name
    
    with tempfile.NamedTemporaryFile(delete=False, mode='wb') as kf:
        kf.write(b"test_key_1234567890")
        kf.flush()
        key_file = kf.name
    
    try:
        hmac_key, _ = derive_keys(key_file)
        hmac_tag = compute_hmac(test_file, hmac_key)
        
        # Check HMAC is 64 hex characters (SHA-256 in hex)
        assert isinstance(hmac_tag, str)
        assert len(hmac_tag) == 64
        assert all(c in '0123456789abcdef' for c in hmac_tag)
        
        # Check HMAC is consistent
        hmac_tag2 = compute_hmac(test_file, hmac_key)
        assert hmac_tag == hmac_tag2
        
        # Check HMAC changes when file changes
        with open(test_file, 'a') as f:
            f.write("\nmodified")
        hmac_tag3 = compute_hmac(test_file, hmac_key)
        assert hmac_tag != hmac_tag3
        
    finally:
        os.unlink(test_file)
        os.unlink(key_file)

