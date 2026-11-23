# -*- coding: utf-8 -*-
"""Localize resources.arsc: rewrite string *values* in place (no new entries)."""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from translate import pool_strings, build_pool_utf16
from arsc_map import load, find_key_entry

# key name -> (value index in the global string pool, Russian text)
RU = {
 'dialog_cancel':                             'Отмена',
 'dialog_download':                           'Скачать',
 'dialog_ok':                                 'ОК',
 'error_engine_setup_message':                 'Не удалось запустить движок Godot! Работа прервана…',
 'error_missing_vulkan_requirements_message':  'Внимание — это устройство не соответствует требованиям для поддержки Vulkan',
 'gabe_connection_error_message':             'Не удалось подключиться к среде сборки Godot для Android (GABE). Убедитесь, что она установлена на вашем устройстве.',
 'gabe_connection_error_title':               'Не удалось подключиться!',
 'text_error_title':                          'Ошибка!',
}
# deliberately NOT translated (must stay English / are brand or format tokens):
#   godot_project_name_string  -> "Ascension Sandbox"  (game title, brand)
#   status_bar_notification_info_overflow -> "999+"    (format token)
#   androidx_startup -> "androidx.startup"              (library metadata, must be exact)

def main(src, dst):
    d, info = load(src)
    d = bytearray(d)
    vals, vinfo = pool_strings(d, 12)
    new = list(vals)
    used = {}
    for key, ru in RU.items():
        k = info['keys'].index(key)
        p, e, hs, ent = find_key_entry(d, info['pk'], 11, k, info['pkgsize'])
        assert e is not None, key
        vdata = struct.unpack('<I', d[e+12:e+16])[0]
        assert vdata not in used, 'pool index %d already retranslated by %s' % (vdata, used.get(vdata))
        assert vals[vdata] not in used, 'source string %r shared' % vals[vdata]
        used[vdata] = key
        print('  [%3d] %-6s %-66r -> %r' % (vdata, '', vals[vdata], ru))
        new[vdata] = ru
    new_pool = build_pool_utf16(new, flags=vinfo['flags'])
    delta = len(new_pool) - vinfo['size']
    nd = bytearray(d[:12] + new_pool + d[12+vinfo['size']:])
    struct.pack_into('<I', nd, 4, len(nd))
    pk = info['pk']
    struct.pack_into('<I', nd, pk+4, struct.unpack('<I', nd[pk+4:pk+8])[0] + delta)
    open(dst, 'wb').write(bytes(nd))
    print('value pool %d -> %d bytes (%+d), file %d -> %d' % (vinfo['size'], len(new_pool), delta, len(d), len(nd)))

# ---------- AXML layouts with hardcoded text ----------
AXML_RU = {
 'res/layout/custom_dialog.xml': {6: ' ОК '},
 'res/layout/snackbar.xml':      {15: 'Действие'},
}

def enc_len8(n):
    if n > 0x7f: return bytes([0x80 | (n >> 8), n & 0xff])
    return bytes([n])

def build_pool_utf8(strings):
    hs=28; n=len(strings); offs=[]; data=b''
    for s in strings:
        offs.append(len(data))
        b=s.encode('utf-8')
        u16=len(s.encode('utf-16-le'))//2
        data += enc_len8(u16) + enc_len8(len(b)) + b + b'\x00'
    while len(data)%4: data += b'\x00'
    str_start=hs+4*n; size=str_start+len(data)
    hdr=struct.pack('<HHI', 1, hs, size)+struct.pack('<IIIII', n,0,0x100,str_start,0)
    return hdr+struct.pack('<%dI'%n, *offs)+data

def localize_axml(src, dst, mapping):
    d=open(src,'rb').read()
    hs=struct.unpack('<H', d[2:4])[0]
    p=hs
    while True:
        t,ch_hs,sz=struct.unpack('<HHI', d[p:p+8])
        if t==1: break
        p+=sz
    strings, info = pool_strings(d, p)
    new=list(strings)
    for i,v in mapping.items():
        print('   [%s] %r -> %r' % (src.split('/')[-1], strings[i], v))
        new[i]=v
    new_pool = build_pool_utf8(new)
    nd=bytearray(d[:p]+new_pool+d[p+info['size']:])
    struct.pack_into('<I', nd, 4, len(nd))
    open(dst,'wb').write(bytes(nd))
    return len(d), len(nd)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
