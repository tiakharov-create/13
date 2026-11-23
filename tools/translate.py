# -*- coding: utf-8 -*-
"""Rebuild the string pool inside a compiled Android resource file / binary XML."""
import struct, sys, shutil

def enc_len16(n):
    if n > 0x7fff: return struct.pack('<HH', 0x8000 | (n >> 16), n & 0xffff)
    return struct.pack('<H', n)

def build_pool_utf16(strings, flags=0):
    hs = 28
    n = len(strings)
    offs, data = [], b''
    for s in strings:
        offs.append(len(data))
        b = s.encode('utf-16-le')
        data += enc_len16(len(b)//2) + b + b'\x00\x00'
    while len(data) % 4: data += b'\x00'
    str_start = hs + 4*n
    size = str_start + len(data)
    hdr = struct.pack('<HHI', 0x0001, hs, size) + struct.pack('<IIIII', n, 0, flags, str_start, 0)
    return hdr + struct.pack('<%dI' % n, *offs) + data

def pool_strings(d, off):
    t, hs, size = struct.unpack('<HHI', d[off:off+8])
    assert t == 1
    count, styles, flags, str_start, style_start = struct.unpack('<IIIII', d[off+8:off+28])
    utf8 = bool(flags & 0x100)
    out = []
    for i in range(count):
        o = struct.unpack('<I', d[off+hs+4*i:off+hs+4*i+4])[0]
        p = off + str_start + o
        out.append(_read(d, p, utf8))
    return out, dict(count=count, styles=styles, flags=flags, utf8=utf8, size=size, hs=hs)

def _len8(d, p):
    b = d[p]; p += 1
    if b & 0x80: return ((b & 0x7f) << 8) | d[p], p+1
    return b, p

def _len16(d, p):
    v = struct.unpack('<H', d[p:p+2])[0]; p += 2
    if v & 0x8000:
        v2 = struct.unpack('<H', d[p:p+2])[0]
        return ((v & 0x7fff) << 16) | v2, p+2
    return v, p

def _read(d, p, utf8):
    if utf8:
        _, p = _len8(d, p); n, p = _len8(d, p)
        return d[p:p+n].decode('utf-8')
    n, p = _len16(d, p)
    return d[p:p+n*2].decode('utf-16-le')

def replace_in_pool(d, pool_off, mapping, rebuild_only=False):
    """mapping: dict index -> new string. Returns (new_bytes, delta)."""
    strings, info = pool_strings(d, pool_off)
    if info['styles']:
        raise SystemExit('pool has styles, not supported')
    for i, new in mapping.items():
        strings[i] = new
    new_pool = build_pool_utf16(strings, flags=info['flags'])
    old_size = info['size']
    new_d = d[:pool_off] + new_pool + d[pool_off+old_size:]
    delta = len(new_pool) - old_size
    return new_d, delta, old_size

def fix_arsc_header(d, delta):
    d = bytearray(d)
    total, = struct.unpack('<I', d[4:8])
    struct.pack_into('<I', d, 4, total + delta)
    # package chunk size (last chunk of the table)
    p = 12 + struct.unpack('<I', d[12+4:12+8])[0]  # skip pool
    p = struct.unpack('<I', d[12+4:12+8])[0] + 12
    t, hs, sz = struct.unpack('<HHI', d[p:p+8])
    assert t == 0x0200, hex(t)
    struct.pack_into('<I', d, p+4, sz + delta)
    return bytes(d)

def fix_axml_header(d, delta):
    d = bytearray(d)
    total, = struct.unpack('<I', d[4:8])
    struct.pack_into('<I', d, 4, total + delta)
    return bytes(d)

if __name__ == '__main__':
    pass
