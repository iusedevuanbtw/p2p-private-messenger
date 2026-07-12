import os
import base64
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
from cryptography.hazmat.primitives import serialization

class E2EEncryption:
    def __init__(self):
        self.private_key = None
        self.public_key = None
        self.peer_public_keys = {}
        self.aes_keys = {}
        self.generate_keypair()

    def generate_keypair(self):
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()

    def get_public_key_pem(self):
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()

    def load_peer_public_key(self, peer_id, pem_data):
        self.peer_public_keys[peer_id] = serialization.load_pem_public_key(pem_data.encode())

    def generate_aes_key(self):
        return os.urandom(32)

    def rsa_encrypt(self, peer_id, data):
        if peer_id not in self.peer_public_keys:
            return None
        public_key = self.peer_public_keys[peer_id]
        encrypted = public_key.encrypt(
            data,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return base64.b64encode(encrypted).decode()

    def rsa_decrypt(self, encrypted_data):
        encrypted_bytes = base64.b64decode(encrypted_data)
        return self.private_key.decrypt(
            encrypted_bytes,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

    def aes_encrypt(self, key, plaintext):
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext.encode()) + padder.finalize()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        return base64.b64encode(iv + ciphertext).decode()

    def aes_decrypt(self, key, encrypted_data):
        data = base64.b64decode(encrypted_data)
        iv = data[:16]
        ciphertext = data[16:]
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded_data) + unpadder.finalize()
        return plaintext.decode()

    def establish_aes_key(self, peer_id, encrypted_aes_key):
        aes_key = self.rsa_decrypt(encrypted_aes_key)
        self.aes_keys[peer_id] = aes_key
        return aes_key

    def encrypt_message(self, peer_id, message):
        if peer_id not in self.aes_keys:
            return None
        return self.aes_encrypt(self.aes_keys[peer_id], message)

    def decrypt_message(self, peer_id, encrypted_message):
        if peer_id not in self.aes_keys:
            return None
        return self.aes_decrypt(self.aes_keys[peer_id], encrypted_message)
