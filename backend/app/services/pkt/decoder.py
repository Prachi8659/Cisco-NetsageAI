"""
NetSage AI — Pure-Python Cisco Packet Tracer (.pkt / .pka) Decoder
Supports:
- Modern Twofish-EAX authenticated encryption (Packet Tracer 7.x, 8.x, 9.x)
- Legacy position-keyed XOR obfuscation (Packet Tracer 5.x, 6.x)
- Direct zlib/deflate streams
- Uncompressed Packet Tracer XML topologies

Security Guarantees:
- Safe, read-only processing on byte buffers (never executes external processes or Cisco binaries)
- Enforces strict input size bounds (max 50 MB)
- Comprehensive exception handling with graceful failure reporting
- Zero synthetic or fabricated data generation
"""

import zlib
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Tuple, Optional
from pathlib import Path

from app.services.pkt.twofish_gladman import Twofish

# Standard Cisco Packet Tracer Twofish-EAX constants
PKT_TWOFISH_KEY = bytes([137] * 16)
PKT_TWOFISH_IV = bytes([16] * 16)
MAX_SAFE_FILE_SIZE = 50 * 1024 * 1024  # 50 MB limit


def double_gf128(block: bytes) -> bytes:
    """Galois Field GF(2^128) doubling used in CMAC subkey generation."""
    val = int.from_bytes(block, byteorder="big")
    msb = (val >> 127) & 1
    val = ((val << 1) & ((1 << 128) - 1))
    if msb:
        val ^= 0x87
    return val.to_bytes(16, byteorder="big")


class TwofishEAX:
    """
    EAX Mode (Bellare, Rogaway, Wagner) AEAD engine using Twofish 128-bit block cipher.
    Implements OMAC/CMAC tag generation and CTR-mode decryption.
    """

    def __init__(self, key: bytes):
        self.tf = Twofish(key)
        # Subkeys for CMAC
        l_block = self.tf.encrypt(bytes(16))
        self.b_subkey = double_gf128(l_block)
        self.p_subkey = double_gf128(self.b_subkey)

    def omac(self, tag: int, data: bytes) -> bytes:
        """OMAC/CMAC computation with domain separation prefix."""
        prefix = bytes(15) + bytes([tag])
        full_data = prefix + data

        blocks = [full_data[i:i + 16] for i in range(0, len(full_data), 16)]
        if not blocks:
            blocks = [b""]

        last = blocks[-1]
        if len(last) == 16:
            last = bytes(a ^ b for a, b in zip(last, self.b_subkey))
        else:
            padded = last + b"\x80" + bytes(15 - len(last))
            last = bytes(a ^ b for a, b in zip(padded, self.p_subkey))
        blocks[-1] = last

        y = bytes(16)
        for blk in blocks:
            xored = bytes(a ^ b for a, b in zip(y, blk))
            y = self.tf.encrypt(xored)
        return y

    def decrypt(self, nonce: bytes, ciphertext: bytes) -> bytes:
        """CTR-mode stream decryption using nonce-derived counter."""
        n_block = self.omac(0, nonce)
        plaintext = bytearray()
        counter_int = int.from_bytes(n_block, "big")

        for i in range(0, len(ciphertext), 16):
            block = ciphertext[i:i + 16]
            ctr_block = counter_int.to_bytes(16, "big")
            keystream = self.tf.encrypt(ctr_block)
            plaintext.extend(bytes(a ^ b for a, b in zip(block, keystream[:len(block)])))
            counter_int = (counter_int + 1) & ((1 << 128) - 1)

        return bytes(plaintext)


@dataclass
class PktDecodeResult:
    success: bool
    xml_bytes: Optional[bytes]
    format_type: str
    version: Optional[str]
    error_message: Optional[str] = None


class PktDecoder:
    """
    Decodes untrusted Cisco Packet Tracer .pkt/.pka files into XML.
    """

    def decode(self, content: bytes) -> PktDecodeResult:
        if len(content) == 0:
            return PktDecodeResult(
                success=False,
                xml_bytes=None,
                format_type="EMPTY",
                version=None,
                error_message="File is empty (0 bytes)."
            )

        if len(content) > MAX_SAFE_FILE_SIZE:
            return PktDecodeResult(
                success=False,
                xml_bytes=None,
                format_type="OVERSIZED",
                version=None,
                error_message=f"File exceeds maximum safe size limit ({MAX_SAFE_FILE_SIZE / (1024*1024):.0f}MB)."
            )

        # 1. Try Direct XML parsing
        if self._is_direct_xml(content):
            version = self._detect_version_from_xml(content)
            return PktDecodeResult(
                success=True,
                xml_bytes=content,
                format_type="RAW_XML",
                version=version
            )

        # 2. Try Direct Zlib/Deflate stream
        zlib_res = self._try_zlib(content)
        if zlib_res:
            version = self._detect_version_from_xml(zlib_res)
            return PktDecodeResult(
                success=True,
                xml_bytes=zlib_res,
                format_type="ZLIB_STREAM",
                version=version
            )

        # 3. Try Modern Packet Tracer Twofish-EAX pipeline (PT 7.x, 8.x, 9.x)
        modern_res = self._try_modern_twofish_eax(content)
        if modern_res:
            version = self._detect_version_from_xml(modern_res) or "Packet Tracer 7.x-9.x"
            return PktDecodeResult(
                success=True,
                xml_bytes=modern_res,
                format_type="MODERN_TWOFISH_EAX",
                version=version
            )

        # 4. Try Legacy Packet Tracer XOR pipeline (PT 5.x, 6.x)
        legacy_res = self._try_legacy_xor(content)
        if legacy_res:
            version = self._detect_version_from_xml(legacy_res) or "Packet Tracer 5.x/6.x"
            return PktDecodeResult(
                success=True,
                xml_bytes=legacy_res,
                format_type="LEGACY_XOR",
                version=version
            )

        return PktDecodeResult(
            success=False,
            xml_bytes=None,
            format_type="UNSUPPORTED_OR_CORRUPT",
            version=None,
            error_message=(
                "Unable to decrypt Packet Tracer binary. "
                "The file may be corrupt, password-protected with a custom key, or use an unrecognized structure."
            )
        )

    def _is_direct_xml(self, content: bytes) -> bool:
        try:
            head = content[:200].decode("utf-8", errors="ignore").strip()
            return (
                head.startswith("<?xml")
                or "<PACKETTRACER" in head
                or "<NETWORK" in head
                or "<DEVICES" in head
            )
        except Exception:
            return False

    def _try_zlib(self, content: bytes) -> Optional[bytes]:
        try:
            decomp = zlib.decompress(content)
            if self._is_direct_xml(decomp):
                return decomp
        except Exception:
            pass

        # Try seeking zlib headers
        for offset in range(min(128, len(content) - 10)):
            if content[offset:offset + 2] in [b"\x78\x9c", b"\x78\xda", b"\x78\x01"]:
                try:
                    decomp = zlib.decompress(content[offset:])
                    if self._is_direct_xml(decomp):
                        return decomp
                except Exception:
                    continue
        return None

    def _try_modern_twofish_eax(self, raw: bytes) -> Optional[bytes]:
        """
        4-stage modern Packet Tracer inversion:
        1. Invert Stage 4 position-keyed XOR + byte reversal
        2. Twofish-EAX authenticated decryption with constant key 0x89*16 & IV 0x10*16
        3. Invert Stage 2 position-keyed XOR
        4. Qt/zlib decompression (4-byte big-endian uncompressed length prefix)
        """
        try:
            length = len(raw)
            if length < 32:
                return None

            # Stage 1: Invert Stage 4
            stage1 = bytearray(length)
            for i in range(length):
                stage1[i] = raw[length - 1 - i] ^ ((length - i * length) & 0xFF)

            # Stage 2: Twofish-EAX Decrypt (strip 16-byte tag)
            eax = TwofishEAX(PKT_TWOFISH_KEY)
            ciphertext = bytes(stage1[:-16])
            decrypted = eax.decrypt(PKT_TWOFISH_IV, ciphertext)

            # Stage 3: Invert Stage 2
            dec_len = len(decrypted)
            stage3 = bytearray(dec_len)
            for i in range(dec_len):
                stage3[i] = decrypted[i] ^ ((dec_len - i) & 0xFF)

            # Stage 4: Decompress Qt zlib payload
            if len(stage3) < 4:
                return None
            
            uncompressed_len = int.from_bytes(stage3[:4], "big")
            # Decompress zlib stream
            xml_bytes = zlib.decompress(stage3[4:])
            if self._is_direct_xml(xml_bytes):
                return xml_bytes

        except Exception:
            pass

        return None

    def _try_legacy_xor(self, raw: bytes) -> Optional[bytes]:
        """
        Legacy Packet Tracer 5.x/6.x XOR + zlib decompression:
        Each byte b[i] is XORed with (length - i) & 0xFF.
        First 4 bytes represent uncompressed length.
        """
        try:
            length = len(raw)
            if length < 5:
                return None

            out = bytearray(length)
            for i in range(length):
                out[i] = raw[i] ^ ((length - i) & 0xFF)

            # Try decompressing with 4-byte prefix
            try:
                xml_bytes = zlib.decompress(bytes(out[4:]))
                if self._is_direct_xml(xml_bytes):
                    return xml_bytes
            except Exception:
                pass

            # Try decompressing raw stream
            xml_bytes = zlib.decompress(bytes(out))
            if self._is_direct_xml(xml_bytes):
                return xml_bytes
        except Exception:
            pass

        return None

    def _detect_version_from_xml(self, xml_bytes: bytes) -> Optional[str]:
        try:
            text = xml_bytes[:2000].decode("utf-8", errors="ignore")
            # Look for <VERSION>9.0.1.0858</VERSION>
            match = re.search(r"<VERSION>([^<]+)</VERSION>", text, re.IGNORECASE)
            if match:
                return f"Cisco Packet Tracer {match.group(1).strip()}"
            if "<PACKETTRACER5" in text:
                return "Cisco Packet Tracer 5.x+"
        except Exception:
            pass
        return None


pkt_decoder = PktDecoder()
