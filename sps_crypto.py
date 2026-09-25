"""
sps_crypto.py - Secure Decryption Engine for .sps Image Files.

Uses AES-256-GCM authenticated decryption to read .sps files directly in memory.
"""

import os
import json
import struct
from typing import Tuple, Dict, Any, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

MAGIC_HEADER = b"SPS1"
DEFAULT_PASSPHRASE = "SPS_SECURE_IMAGE_VIEWER_2026_KEY"
SALT_SIZE = 16
NONCE_SIZE = 12
TAG_SIZE = 16
PBKDF2_ITERATIONS = 100_000

# Thread-safe directory creation cache
_dir_cache: set = set()
_dir_cache_lock = __import__("threading").Lock()


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a 256-bit cryptographic key from a passphrase and salt using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def is_sps_file(file_path: str) -> bool:
    """Check if the specified file has the valid .sps magic header."""
    if not os.path.exists(file_path):
        return False
    try:
        with open(file_path, "rb") as f:
            header = f.read(len(MAGIC_HEADER))
            return header == MAGIC_HEADER
    except Exception:
        return False


def decrypt_sps_file(
    sps_path: str,
    passphrase: str = DEFAULT_PASSPHRASE
) -> Tuple[bytes, Dict[str, Any]]:
    """Decrypt a .sps file directly into RAM memory."""
    sps_abs_path = os.path.abspath(sps_path)
    if not os.path.isfile(sps_abs_path):
        raise FileNotFoundError(f".sps file not found: {sps_abs_path}")

    with open(sps_abs_path, "rb") as f:
        magic = f.read(len(MAGIC_HEADER))
        if magic != MAGIC_HEADER:
            raise ValueError(f"Invalid file format: Header does not match {MAGIC_HEADER.decode()}")
        
        salt = f.read(SALT_SIZE)
        nonce = f.read(NONCE_SIZE)
        tag = f.read(TAG_SIZE)
        ciphertext = f.read()

    key = _derive_key(passphrase, salt)
    aesgcm = AESGCM(key)

    encrypted_blob = ciphertext + tag

    try:
        payload = aesgcm.decrypt(nonce, encrypted_blob, MAGIC_HEADER)
    except Exception as e:
        raise ValueError("Decryption failed. Invalid passphrase or corrupted file integrity.") from e

    meta_len = struct.unpack(">I", payload[:4])[0]
    meta_bytes = payload[4:4 + meta_len]
    image_bytes = payload[4 + meta_len:]

    metadata = json.loads(meta_bytes.decode("utf-8")) if meta_bytes else {}
    return image_bytes, metadata


def derive_session_key(passphrase: str = DEFAULT_PASSPHRASE) -> Tuple[bytes, bytes]:
    """Derive a session-level AES-256 key from a passphrase with a fresh random salt.

    Returns:
        (key, salt): The derived 32-byte key and the 16-byte salt used.
    """
    salt = os.urandom(SALT_SIZE)
    key = _derive_key(passphrase, salt)
    return key, salt


def encrypt_image_data(
    image_bytes: bytes,
    dest_path: str,
    passphrase: str = DEFAULT_PASSPHRASE,
    metadata: Optional[Dict[str, Any]] = None,
    derived_key: Optional[bytes] = None,
    salt: Optional[bytes] = None,
    cipher: Optional[AESGCM] = None,
) -> str:
    """Encrypt raw image bytes and write them to a .sps file.

    When *derived_key*, *salt*, and *cipher* are supplied (session-level pre-derivation),
    the expensive PBKDF2 step is skipped — enabling near-instant per-file encryption.

    Args:
        image_bytes:  Raw bytes of the (optionally pre-compressed) image.
        dest_path:    Absolute path of the output .sps file.
        passphrase:   Passphrase used only when *derived_key* is not provided.
        metadata:     Optional dict of metadata stored inside the .sps container.
        derived_key:  Pre-derived 32-byte AES key (skip PBKDF2 when provided).
        salt:         16-byte salt matching *derived_key* (required with derived_key).
        cipher:       Pre-constructed AESGCM instance (skip construction when provided).

    Returns:
        The absolute path of the written .sps file.
    """
    if metadata is None:
        metadata = {}

    # Key derivation — use pre-derived session key when available for speed.
    if derived_key is not None and salt is not None:
        key = derived_key
        used_salt = salt
    else:
        used_salt = os.urandom(SALT_SIZE)
        key = _derive_key(passphrase, used_salt)

    if cipher is None:
        cipher = AESGCM(key)

    # Build the plaintext payload:  [4-byte meta_len][meta JSON][image bytes]
    meta_bytes = json.dumps(metadata, separators=(",", ":")).encode("utf-8")
    meta_len_prefix = struct.pack(">I", len(meta_bytes))
    payload = meta_len_prefix + meta_bytes + image_bytes

    # Encrypt with AES-256-GCM; AAD = magic header for integrity binding.
    nonce = os.urandom(NONCE_SIZE)
    encrypted_blob = cipher.encrypt(nonce, payload, MAGIC_HEADER)

    # AES-GCM appends the 16-byte tag at the end of the ciphertext blob.
    ciphertext = encrypted_blob[:-TAG_SIZE]
    tag = encrypted_blob[-TAG_SIZE:]

    # Thread-safe, cached directory creation to avoid redundant syscalls.
    dest_dir = os.path.dirname(os.path.abspath(dest_path))
    with _dir_cache_lock:
        if dest_dir not in _dir_cache:
            os.makedirs(dest_dir, exist_ok=True)
            _dir_cache.add(dest_dir)

    # Single-syscall binary write: MAGIC | SALT | NONCE | TAG | CIPHERTEXT
    with open(dest_path, "wb") as f:
        f.write(MAGIC_HEADER + used_salt + nonce + tag + ciphertext)

    return dest_path
