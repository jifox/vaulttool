import subprocess

def encrypt_file(input_path, output_path, key_file, algorithm, openssl_path="openssl"):
    cmd = [
        openssl_path, "enc", f"-{algorithm}",
        "-salt", "-in", input_path,
        "-out", output_path,
        "-pass", f"file:{key_file}"
    ]
    subprocess.run(cmd, check=True)
