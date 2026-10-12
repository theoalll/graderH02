"""
Twofish-EAX & Byte Reversal Decryption Module for Cisco Packet Tracer (.pkt/.pka) files.

Acknowledgment & Citation:
Based on the Twofish-EAX authenticated encryption specification and reverse-engineered
algorithm implemented by the creators of Packet Tracer Converter (https://pt-convert.podik.cz/).
"""

from __future__ import annotations
import struct
import zlib
from pathlib import Path
from typing import BinaryIO

# Fixed Permutations P0 & P1
P0 = [
    169, 103, 179, 232, 4, 253, 163, 118, 154, 146, 128, 120, 228, 221, 209, 56, 13, 198, 53, 152,
    24, 247, 236, 108, 67, 117, 55, 38, 250, 19, 148, 72, 242, 208, 139, 48, 132, 84, 223, 35, 25,
    91, 61, 89, 243, 174, 162, 130, 99, 1, 131, 46, 217, 81, 155, 124, 166, 235, 165, 190, 22, 12,
    227, 97, 192, 140, 58, 245, 115, 44, 37, 11, 187, 78, 137, 107, 83, 106, 180, 241, 225, 230,
    189, 69, 226, 244, 182, 102, 204, 149, 3, 86, 212, 28, 30, 215, 251, 195, 142, 181, 233, 207,
    191, 186, 234, 119, 57, 175, 51, 201, 98, 113, 129, 121, 9, 173, 36, 205, 249, 216, 229, 197,
    185, 77, 68, 8, 134, 231, 161, 29, 170, 237, 6, 112, 178, 210, 65, 123, 160, 17, 49, 194, 39,
    144, 32, 246, 96, 255, 150, 92, 177, 171, 158, 156, 82, 27, 95, 147, 10, 239, 145, 133, 73,
    238, 45, 79, 143, 59, 71, 135, 109, 70, 214, 62, 105, 100, 42, 206, 203, 47, 252, 151, 5,
    122, 172, 127, 213, 26, 75, 14, 167, 90, 40, 20, 63, 41, 136, 60, 76, 2, 184, 218, 176, 23,
    85, 31, 138, 125, 87, 199, 141, 116, 183, 196, 159, 114, 126, 21, 34, 18, 88, 7, 153, 52,
    110, 80, 222, 104, 101, 188, 219, 248, 200, 168, 43, 64, 220, 254, 50, 164, 202, 16, 33, 240,
    211, 93, 15, 0, 111, 157, 54, 66, 74, 94, 193, 224
]

P1 = [
    117, 243, 198, 244, 219, 123, 251, 200, 74, 211, 230, 107, 69, 125, 232, 75, 214, 50, 216, 253,
    55, 113, 241, 225, 48, 15, 248, 27, 135, 250, 6, 63, 94, 186, 174, 91, 138, 0, 188, 157, 109,
    193, 177, 14, 128, 93, 210, 213, 160, 132, 7, 20, 181, 144, 44, 163, 178, 115, 76, 84, 146,
    116, 54, 81, 56, 176, 189, 90, 252, 96, 98, 150, 108, 66, 247, 16, 124, 40, 39, 140, 19, 149,
    156, 199, 36, 70, 59, 112, 202, 227, 133, 203, 17, 208, 147, 184, 166, 131, 32, 255, 159, 119,
    195, 204, 3, 111, 8, 191, 64, 231, 43, 226, 121, 12, 170, 130, 65, 58, 234, 185, 228, 154,
    164, 151, 126, 218, 122, 23, 102, 148, 161, 29, 61, 240, 222, 179, 11, 114, 167, 28, 239, 209,
    83, 62, 143, 51, 38, 95, 236, 118, 42, 73, 129, 136, 238, 33, 196, 26, 235, 217, 197, 57,
    153, 205, 173, 49, 139, 1, 24, 35, 221, 31, 78, 45, 249, 72, 79, 242, 101, 142, 120, 92,
    88, 25, 141, 229, 152, 87, 103, 127, 5, 100, 175, 99, 182, 254, 245, 183, 60, 165, 206, 233,
    104, 68, 224, 77, 67, 105, 41, 46, 172, 21, 89, 168, 10, 158, 110, 71, 223, 52, 53, 106,
    207, 220, 34, 201, 192, 155, 137, 212, 237, 171, 18, 162, 13, 82, 187, 2, 47, 169, 215, 97,
    30, 180, 80, 4, 246, 194, 22, 37, 134, 86, 85, 9, 190, 145
]

P = [P0, P1]

SK_STEP = 0x02020202
SK_BUMP = 0x01010101
SK_ROTL = 9
ROUNDS = 16
ROUND_SUBKEYS = 8
TOTAL_SUBKEYS = ROUND_SUBKEYS + 2 * ROUNDS  # 40
P_00 = 1; P_01 = 0; P_02 = 0; P_03 = 1; P_04 = 1
P_10 = 0; P_11 = 0; P_12 = 1; P_13 = 1; P_14 = 0
P_20 = 1; P_21 = 1; P_22 = 0; P_23 = 0; P_24 = 0
P_30 = 0; P_31 = 1; P_32 = 1; P_33 = 0; P_34 = 1
GF256_FDBK_2 = 0x169 // 2
GF256_FDBK_4 = 0x169 // 4
RS_GF_FDBK = 0x14D

FIXED_KEY = bytes([137] * 16)
FIXED_IV = bytes([16] * 16)

def i32(v: int) -> int:
    v = v & 0xFFFFFFFF
    return v if v <= 0x7FFFFFFF else v - 0x100000000

def u32(v: int) -> int: return v & 0xFFFFFFFF

def lfsr1(x: int) -> int: return i32(((x >> 1) & 0xFF) ^ (GF256_FDBK_2 if (x & 0x01) else 0))
def lfsr2(x: int) -> int: return i32(((x >> 2) & 0xFF) ^ (GF256_FDBK_2 if (x & 0x02) else 0) ^ (GF256_FDBK_4 if (x & 0x01) else 0))
def mxX(x: int) -> int: return i32(x ^ lfsr2(x))
def mxY(x: int) -> int: return i32(x ^ lfsr1(x) ^ lfsr2(x))

MDS = [[0]*256 for _ in range(4)]
for i in range(256):
    j0 = P[0][i] & 0xFF
    j1 = P[1][i] & 0xFF

    m1 = [j0, j1]
    mX = [mxX(j0) & 0xFF, mxX(j1) & 0xFF]
    mY = [mxY(j0) & 0xFF, mxY(j1) & 0xFF]

    MDS[0][i] = i32(m1[P_00] | (mX[P_00] << 8) | (mY[P_00] << 16) | (mY[P_00] << 24))
    MDS[1][i] = i32(mY[P_10] | (mY[P_10] << 8) | (mX[P_10] << 16) | (m1[P_10] << 24))
    MDS[2][i] = i32(mX[P_20] | (mY[P_20] << 8) | (m1[P_20] << 16) | (mY[P_20] << 24))
    MDS[3][i] = i32(mX[P_30] | (m1[P_30] << 8) | (mY[P_30] << 16) | (mX[P_30] << 24))

def b0(x: int) -> int: return x & 0xFF
def b1(x: int) -> int: return (x >> 8) & 0xFF if x >= 0 else (x & 0xFFFFFFFF) >> 8 & 0xFF
def b2(x: int) -> int: return (x >> 16) & 0xFF if x >= 0 else (x & 0xFFFFFFFF) >> 16 & 0xFF
def b3(x: int) -> int: return (x >> 24) & 0xFF if x >= 0 else (x & 0xFFFFFFFF) >> 24 & 0xFF

def rsRem(x: int) -> int:
    b = b3(x)
    g2 = i32(((b << 1) ^ (RS_GF_FDBK if (b & 0x80) else 0))) & 0xFF
    g3 = i32(((b >> 1) ^ ((RS_GF_FDBK >> 1) if (b & 0x01) else 0) ^ g2)) & 0xFF
    return i32((x << 8) ^ (g3 << 24) ^ (g2 << 16) ^ (g3 << 8) ^ b)

def rsMDSEncode(k0: int, k1: int) -> int:
    for _ in range(4): k1 = rsRem(k1)
    k1 = i32(k1 ^ k0)
    for _ in range(4): k1 = rsRem(k1)
    return i32(k1)

def f32(k64Cnt: int, x: int, k32: list[int]) -> int:
    lB0, lB1, lB2, lB3 = b0(x), b1(x), b2(x), b3(x)
    k0 = k32[0] if len(k32) > 0 else 0
    k1 = k32[1] if len(k32) > 1 else 0
    k2 = k32[2] if len(k32) > 2 else 0
    k3 = k32[3] if len(k32) > 3 else 0

    mode = k64Cnt & 3
    if mode == 1:
        return i32(MDS[0][P[P_01][lB0] ^ b0(k0)] ^
                   MDS[1][P[P_11][lB1] ^ b1(k0)] ^
                   MDS[2][P[P_21][lB2] ^ b2(k0)] ^
                   MDS[3][P[P_31][lB3] ^ b3(k0)])
    
    if mode == 0:
        lB0 = P[P_04][lB0] ^ b0(k3)
        lB1 = P[P_14][lB1] ^ b1(k3)
        lB2 = P[P_24][lB2] ^ b2(k3)
        lB3 = P[P_34][lB3] ^ b3(k3)
        mode = 3

    if mode == 3:
        lB0 = P[P_03][lB0] ^ b0(k2)
        lB1 = P[P_13][lB1] ^ b1(k2)
        lB2 = P[P_23][lB2] ^ b2(k2)
        lB3 = P[P_33][lB3] ^ b3(k2)
        mode = 2

    if mode == 2:
        return i32(MDS[0][P[P_01][P[P_02][lB0] ^ b0(k1)] ^ b0(k0)] ^
                   MDS[1][P[P_11][P[P_12][lB1] ^ b1(k1)] ^ b1(k0)] ^
                   MDS[2][P[P_21][P[P_22][lB2] ^ b2(k1)] ^ b2(k0)] ^
                   MDS[3][P[P_31][P[P_32][lB3] ^ b3(k1)] ^ b3(k0)])
    return 0

def make_session_key(key: bytes) -> tuple[list[int], list[int]]:
    k64Cnt = len(key) // 8
    k32e = []
    k32o = []
    sBoxKey = [0]*4
    offset = 0
    for i in range(min(4, k64Cnt)):
        if offset + 8 <= len(key):
            e = i32(key[offset] | (key[offset+1] << 8) | (key[offset+2] << 16) | (key[offset+3] << 24))
            o = i32(key[offset+4] | (key[offset+5] << 8) | (key[offset+6] << 16) | (key[offset+7] << 24))
            k32e.append(e)
            k32o.append(o)
            sBoxKey[k64Cnt - 1 - i] = rsMDSEncode(e, o)
            offset += 8

    subKeys = [0] * TOTAL_SUBKEYS
    q = 0
    for i in range(TOTAL_SUBKEYS // 2):
        A = f32(k64Cnt, q, k32e)
        B = f32(k64Cnt, q + SK_BUMP, k32o)
        B = i32((B << 8) | u32(B) >> 24)
        A = i32(A + B)
        subKeys[2 * i] = A
        A = i32(A + B)
        subKeys[2 * i + 1] = i32((A << SK_ROTL) | u32(A) >> (32 - SK_ROTL))
        q = i32(q + SK_STEP)

    k0, k1, k2, k3 = sBoxKey[0], sBoxKey[1], sBoxKey[2], sBoxKey[3]
    sBox = [0] * 0x400
    for i in range(256):
        lB0 = lB1 = lB2 = lB3 = i
        mode = k64Cnt & 3
        if mode == 1:
            sBox[2 * i] = MDS[0][P[P_01][lB0] ^ b0(k0)]
            sBox[2 * i + 1] = MDS[1][P[P_11][lB1] ^ b1(k0)]
            sBox[0x200 + 2 * i] = MDS[2][P[P_21][lB2] ^ b2(k0)]
            sBox[0x200 + 2 * i + 1] = MDS[3][P[P_31][lB3] ^ b3(k0)]
        elif mode == 0:
            lB0 = P[P_04][lB0] ^ b0(k3)
            lB1 = P[P_14][lB1] ^ b1(k3)
            lB2 = P[P_24][lB2] ^ b2(k3)
            lB3 = P[P_34][lB3] ^ b3(k3)
            mode = 3
        if mode == 3:
            lB0 = P[P_03][lB0] ^ b0(k2)
            lB1 = P[P_13][lB1] ^ b1(k2)
            lB2 = P[P_23][lB2] ^ b2(k2)
            lB3 = P[P_33][lB3] ^ b3(k2)
            mode = 2
        if mode == 2:
            sBox[2 * i] = MDS[0][P[P_01][P[P_02][lB0] ^ b0(k1)] ^ b0(k0)]
            sBox[2 * i + 1] = MDS[1][P[P_11][P[P_12][lB1] ^ b1(k1)] ^ b1(k0)]
            sBox[0x200 + 2 * i] = MDS[2][P[P_21][P[P_22][lB2] ^ b2(k1)] ^ b2(k0)]
            sBox[0x200 + 2 * i + 1] = MDS[3][P[P_31][P[P_32][lB3] ^ b3(k1)] ^ b3(k0)]

    return sBox, subKeys

def chooseB(x: int, N: int) -> int:
    m = N % 4
    if m == 0: return b0(x)
    if m == 1: return b1(x)
    if m == 2: return b2(x)
    return b3(x)

def fe32(sBox: list[int], x: int, R: int) -> int:
    toReturn = (
        sBox[2 * chooseB(x, R)] ^
        sBox[2 * chooseB(x, R + 1) + 1] ^
        sBox[0x200 + 2 * chooseB(x, R + 2)] ^
        sBox[0x200 + 2 * chooseB(x, R + 3) + 1]
    )
    return i32(toReturn)

def encrypt_block(input_bytes: bytes, session_key: tuple[list[int], list[int]]) -> bytes:
    sBox, sKey = session_key
    x0 = i32(input_bytes[0] | (input_bytes[1] << 8) | (input_bytes[2] << 16) | (input_bytes[3] << 24))
    x1 = i32(input_bytes[4] | (input_bytes[5] << 8) | (input_bytes[6] << 16) | (input_bytes[7] << 24))
    x2 = i32(input_bytes[8] | (input_bytes[9] << 8) | (input_bytes[10] << 16) | (input_bytes[11] << 24))
    x3 = i32(input_bytes[12] | (input_bytes[13] << 8) | (input_bytes[14] << 16) | (input_bytes[15] << 24))

    INPUT_WHITEN = 0
    OUTPUT_WHITEN = 4
    ROUND_SUBKEYS_START = 8

    x0 = i32(x0 ^ sKey[INPUT_WHITEN])
    x1 = i32(x1 ^ sKey[INPUT_WHITEN + 1])
    x2 = i32(x2 ^ sKey[INPUT_WHITEN + 2])
    x3 = i32(x3 ^ sKey[INPUT_WHITEN + 3])

    k = ROUND_SUBKEYS_START
    for R in range(0, ROUNDS, 2):
        t0 = fe32(sBox, x0, 0)
        t1 = fe32(sBox, x1, 3)
        x2 = i32(x2 ^ i32(t0 + t1 + sKey[k]))
        k += 1
        x2 = i32(u32(x2) >> 1 | (x2 << 31))

        x3 = i32((x3 << 1) | u32(x3) >> 31)
        x3 = i32(x3 ^ i32(t0 + 2 * t1 + sKey[k]))
        k += 1

        t0 = fe32(sBox, x2, 0)
        t1 = fe32(sBox, x3, 3)
        x0 = i32(x0 ^ i32(t0 + t1 + sKey[k]))
        k += 1
        x0 = i32(u32(x0) >> 1 | (x0 << 31))

        x1 = i32((x1 << 1) | u32(x1) >> 31)
        x1 = i32(x1 ^ i32(t0 + 2 * t1 + sKey[k]))
        k += 1

    x2 = i32(x2 ^ sKey[OUTPUT_WHITEN])
    x3 = i32(x3 ^ sKey[OUTPUT_WHITEN + 1])
    x0 = i32(x0 ^ sKey[OUTPUT_WHITEN + 2])
    x1 = i32(x1 ^ sKey[OUTPUT_WHITEN + 3])

    return bytes([
        b0(x2), b1(x2), b2(x2), b3(x2),
        b0(x3), b1(x3), b2(x3), b3(x3),
        b0(x0), b1(x0), b2(x0), b3(x0),
        b0(x1), b1(x1), b2(x1), b3(x1)
    ])

SESSION_KEY = make_session_key(FIXED_KEY)

def _shift_left_one_bit(buf: bytearray) -> bytearray:
    out = bytearray(len(buf))
    carry = 0
    for i in range(len(buf) - 1, -1, -1):
        b = buf[i]
        out[i] = ((b << 1) & 0xFF) | carry
        carry = (b & 0x80) >> 7
    return out

def _generate_cmac_subkeys() -> tuple[bytes, bytes]:
    L = encrypt_block(b"\x00" * 16, SESSION_KEY)
    k1 = _shift_left_one_bit(bytearray(L))
    if L[0] & 0x80:
        k1[15] ^= 0x87

    k2 = _shift_left_one_bit(k1)
    if k1[0] & 0x80:
        k2[15] ^= 0x87

    return bytes(k1), bytes(k2)

CMAC_K1, CMAC_K2 = _generate_cmac_subkeys()

def _omac_in_place(tag_byte: int, message: bytes) -> bytes:
    prefix = bytearray(16)
    prefix[15] = tag_byte
    mac = bytearray(16)

    if len(message) == 0:
        last_block = bytearray(16)
        for i in range(16):
            last_block[i] = prefix[i] ^ CMAC_K1[i]
        return encrypt_block(bytes(last_block), SESSION_KEY)

    for i in range(16):
        mac[i] ^= prefix[i]
    mac = bytearray(encrypt_block(bytes(mac), SESSION_KEY))

    length = len(message)
    num_blocks = (length + 15) // 16
    full_blocks = num_blocks - 1

    offset = 0
    for _ in range(full_blocks):
        for i in range(16):
            mac[i] ^= message[offset + i]
        mac = bytearray(encrypt_block(bytes(mac), SESSION_KEY))
        offset += 16

    last_chunk_len = length - offset
    last_block = bytearray(16)
    if last_chunk_len == 16:
        for i in range(16):
            last_block[i] = message[offset + i] ^ CMAC_K1[i]
    else:
        for i in range(last_chunk_len):
            last_block[i] = message[offset + i]
        last_block[last_chunk_len] = 0x80
        for i in range(16):
            last_block[i] ^= CMAC_K2[i]

    for i in range(16):
        mac[i] ^= last_block[i]
    return encrypt_block(bytes(mac), SESSION_KEY)

def _ctr_decrypt_in_place(counter: bytes, data: bytearray) -> None:
    ctr = bytearray(counter)
    offset = 0
    length = len(data)

    while offset < length:
        keystream = encrypt_block(bytes(ctr), SESSION_KEY)
        for i in range(15, -1, -1):
            ctr[i] = (ctr[i] + 1) & 0xFF
            if ctr[i] != 0:
                break
        chunk = min(16, length - offset)
        for i in range(chunk):
            data[offset + i] ^= keystream[i]
        offset += chunk

def _eg_in_place(data: bytearray) -> None:
    length = len(data)
    for i in range(length):
        data[i] ^= ((length - i) & 0xFF)

from ptdecoder.exceptions import PktDecompressionLimitError, PktFileSizeExceededError


def decrypt_pkt(
    source: str | Path | bytes | BinaryIO,
    max_file_size: int | None = 50_000_000,
    max_uncompressed_bytes: int | None = 100_000_000,
) -> bytes:
    """
    Decrypts a Cisco Packet Tracer (.pkt/.pka) file stream or file path into raw uncompressed XML bytes.

    Args:
        source: File path, bytes, or open binary stream (BinaryIO).
        max_file_size: Maximum allowed raw input size in bytes (default: 50MB). Pass None to disable.
        max_uncompressed_bytes: Maximum allowed uncompressed XML payload size (default: 100MB). Pass None to disable.

    Returns:
        Uncompressed XML bytes.

    Raises:
        PktFileSizeExceededError: If raw input file size exceeds max_file_size.
        PktDecompressionLimitError: If uncompressed XML payload exceeds max_uncompressed_bytes.
    """
    if isinstance(source, (str, Path)):
        p = Path(source)
        size = p.stat().st_size
        if max_file_size is not None and size > max_file_size:
            raise PktFileSizeExceededError(f"Raw file size ({size:,} bytes) exceeds safety limit ({max_file_size:,} bytes).")
        with open(p, "rb") as f:
            raw_bytes = f.read()
    elif isinstance(source, bytes):
        if max_file_size is not None and len(source) > max_file_size:
            raise PktFileSizeExceededError(f"Raw bytes length ({len(source):,} bytes) exceeds safety limit ({max_file_size:,} bytes).")
        raw_bytes = source
    elif hasattr(source, "read"):
        raw_bytes = source.read()
        if max_file_size is not None and len(raw_bytes) > max_file_size:
            raise PktFileSizeExceededError(f"Raw stream length ({len(raw_bytes):,} bytes) exceeds safety limit ({max_file_size:,} bytes).")
    else:
        raise TypeError("Invalid source type for decrypt_pkt. Expected file path, bytes, or BinaryIO.")

    length = len(raw_bytes)
    reversed_data = bytearray(length)
    for i in range(length):
        mask = (length - ((i * length) & 0xFFFFFFFF)) & 0xFF
        reversed_data[i] = raw_bytes[length - 1 - i] ^ mask

    ciphertext = reversed_data[: length - 16]

    nonce = _omac_in_place(0, FIXED_IV)
    _ctr_decrypt_in_place(nonce, ciphertext)
    _eg_in_place(ciphertext)

    uncompressed_len = struct.unpack(">I", ciphertext[:4])[0]
    if max_uncompressed_bytes is not None and uncompressed_len > max_uncompressed_bytes:
        raise PktDecompressionLimitError(
            f"Header uncompressed size ({uncompressed_len:,} bytes) exceeds safety limit ({max_uncompressed_bytes:,} bytes)."
        )

    # Streaming zlib decompression guard
    d = zlib.decompressobj()
    compressed_payload = bytes(ciphertext[4:])
    uncompressed = bytearray()
    chunk_size = 64 * 1024

    for i in range(0, len(compressed_payload), chunk_size):
        chunk = compressed_payload[i : i + chunk_size]
        decompressed_chunk = d.decompress(chunk)
        uncompressed.extend(decompressed_chunk)
        if max_uncompressed_bytes is not None and len(uncompressed) > max_uncompressed_bytes:
            raise PktDecompressionLimitError(
                f"Decompressed payload size ({len(uncompressed):,} bytes) exceeds safety limit ({max_uncompressed_bytes:,} bytes)."
            )

    uncompressed.extend(d.flush())
    final_xml = bytes(uncompressed[:uncompressed_len])
    return final_xml
