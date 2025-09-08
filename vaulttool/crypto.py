import subprocess

def encrypt_file(input_path, output_path, key_file, algorithm, openssl_path="openssl"):
    cmd = [
        openssl_path, "enc", f"-{algorithm}",
        "-salt", "-pbkdf2",  # Use PBKDF2 for secure key derivation
        "-in", input_path,
        "-out", output_path,
        "-pass", f"file:{key_file}"
    ]
    subprocess.run(cmd, check=True)
