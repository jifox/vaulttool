import tempfile
import os
from vaulttool.config import load_config

def test_load_config_reads_yaml():
    config_yaml = '''
vaulttool:
  include_directories: ['testdir']
  exclude_directories: []
  include_patterns: ['*.env']
  exclude_patterns: ['*.log']
  options:
    suffix: ".vault"
    openssl_path: "openssl"
    algorithm: "aes-256-cbc"
    key_type: "file"
    key_file: "keyfile"
'''
    with tempfile.NamedTemporaryFile(delete=False, mode="w") as tf:
        tf.write(config_yaml)
        tf.flush()
        config = load_config(tf.name)
        assert config["include_directories"] == ['testdir']
        assert config["options"]["algorithm"] == "aes-256-cbc"
    os.unlink(tf.name)
