# Original work Copyright (C) John Wharton (Solstice245)
# Modified 2026-08-29 by dexmar: Blender 5.1 compatibility; vertex-weld fix
# Licensed under the GNU General Public License v2.0

from os import path
import struct
import math
import re

# modl description
#    tag version bone_offset bone_count vertices_offset vert_unk vertices_count
#    faces_offset face_count info_offset info_count total_bone_count
# bone description
#    4x4 matrix, position xyz, rotation xyzw, name_offset, parent_index, unk0 unk1
# vertice description
#    position xyz, normal xyz, tangent xyz, binormal xyz, uv, uv, bone 0-3
# frame description
#    position xyz, rotation xyzw
# head description
#    time flags
# anim description
#    tag version frames duration bones names_offset links_offset frames_offset frame_size


def pad(size):
    val = 16 - (size % 16)
    return val + 16 if (val < 4) else val


def pad_file(file, s4comment):
    N = pad(file.tell()) - 4
    filldata = b'\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5'
    file.write(struct.pack(str(N)+'s4s', filldata[0:N], s4comment))
    return file.tell()


def read_scm(filepath):
    if path.isfile(filepath): sc = open(filepath, 'rb')
    else: return

    modl = struct.unpack('4s11I', sc.read(48))
    sc.seek(modl[2])
    bones = tuple(struct.iter_unpack('16f3f4f4i', sc.read(108 * modl[11])))
    sc.seek(modl[4])
    verts = tuple(struct.iter_unpack('3f3f3f3f2f2f4B', sc.read(68 * modl[6])))
    sc.seek(modl[7])
    faces = tuple(struct.unpack('H' * modl[8], sc.read(2 * modl[8])))
    sc.seek(modl[9])
    if modl[10]:
        info = struct.unpack('s' * modl[10], sc.read(modl[10]))[0].decode('ascii')

    bone_names = []
    for bone in bones:
        sc.seek(bone[23])
        buffer = b''
        while True:
            b = sc.read(1)
            if b == b'\0': break
            buffer += b
        bone_names.append(buffer.decode('ascii'))

    sc.close()
    return bones, bone_names, verts, faces


def write_scm(filepath, modl, bones, bone_names, verts, faces, info):
    with open(filepath, 'w+b') as f:
        f.write(struct.pack('4s11I', *modl))

        pad_file(f, b'NAME')
        for name in bone_names:
            f.write(struct.pack(f'{str(len(name))}sx', name))
        pad_file(f, b'SKEL')
        f.write(struct.pack('16f3f4f4i' * (len(bones) // 27), *bones))
        pad_file(f, b'VRTX')
        f.write(struct.pack('3f3f3f3f2f2f4B' * (len(verts) // 20), *verts))
        pad_file(f, b'TRIS')
        f.write(struct.pack('H' * len(faces) , *faces))

        if len(info):
            pad_file(f, b'INFO')
            struct.pack(f'{len(info)}s', info)


def read_sca(filepath):
    if path.isfile(filepath): sc = open(filepath, 'rb')
    else: return

    anim = struct.unpack('4sIIfIIIII', sc.read(36))

    link_keys = []
    sc.seek(anim[5])
    for ii in range(anim[4]):
        buffer = b''
        while True:
            b = sc.read(1)
            if b == b'\x00': break
            buffer += b
        link_keys.append(buffer.decode('ascii'))

    # * skipping this as we assume that the skeleton will have the same heirarchy as the scm
    # sc.seek(anim[6])
    # links = struct.unpack(str(anim[4]) + 'i', sc.read(anim[4] * 4))

    sc.seek(anim[7])
    root = struct.unpack('7f', sc.read(28))
    frames = []
    for ii in range(anim[2]):
        header = struct.unpack('fI', sc.read(8))
        data = list(struct.iter_unpack('7f', sc.read(28 * anim[4])))
        frames.append([*header, {link_keys[ii]:data[ii] for ii in range(anim[4])}])

    sc.close()
    return link_keys, frames


def write_sca(filepath, anim, names, links, frames):
    with open(filepath, 'w+b') as f:
        f.write(struct.pack('4siifiiiii', *anim))
        pad_file(f, b'NAME')
        f.write(struct.pack(str(len(names)) + 's', names.encode('ascii')))
        pad_file(f, b'LINK')
        f.write(struct.pack(str(len(links)) + 'i', *links))
        pad_file(f, b'DATA')
        f.write(struct.pack('7f', 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0))
        f.write(struct.pack(f'fi{7 * len(links)}f' * (len(frames) // (7 * len(links) + 2)), *frames))


def read_bp(filepath):
    if path.isfile(filepath): bpf = open(filepath, 'rb').read().decode()
    else: return

    clean_bp = ''
    for ln in bpf.split('\n'):
        clean_bp += ''.join(ln.split('#')[0]).split('--')[0]

    bp = ' '.join(clean_bp.split())

    char_find = {char: bp.find(char) for char in ['{', '}', '=', ',']}
    split = ['', bp]
    split_char = ''
    flat = {}
    keys = []
    key_counter = {}
    string_char = None

    while True:
        last_split_char = split_char
        split_char = sorted((value, key) for key, value in char_find.items())[0][1]

        if string_char:
            char_ii = None
            sub_start = 1
            while sub_start < len(split[1]):
                sub_text = split[1][sub_start:]
                find_ii = sub_text.find(string_char)
                if find_ii > 0:
                    if sub_text[find_ii - 1] == '\\':
                        sub_start += find_ii + 1
                    else:
                        char_ii = sub_start + find_ii
                        break
                else:
                    char_ii = sub_start + find_ii
                    break
            split = split[1][0:char_ii + 1].strip(), split[1][char_ii + 2:].strip()
        else:
            split = split[1].split(split_char, 1)
            split[0] = split[0].strip()
            try: split[1] = split[1].strip()
            except IndexError: break

        char_find = {char: split[1].find(char) for char in ('{', '}', '=', ',')}
        for key in char_find.keys(): char_find[key] = 2**16 if char_find[key] == -1 else char_find[key]

        if split_char == '=': keys.append(split[0])
        elif split_char == '{':
            if last_split_char == '{':
                key_counter['.'.join(keys)] = 0
                keys.append(str(key_counter['.'.join(keys)]))
            elif last_split_char == ',':
                key_counter['.'.join(keys)] += 1
                keys.append(str(key_counter['.'.join(keys)]))
        elif split_char == '}' and last_split_char != '{': keys = keys[:-1]
        elif split_char == ',' and last_split_char != '}':

            val = split[0]

            if string_char: val = val[1:-1]
            else:
                if val.isdigit(): val = int(val)
                elif val in ['true', 'false']: val = val == 'true'
                else: val = float(val)

            if last_split_char == '=':
                flat['.'.join(keys)] = val
                del keys[-1]
            elif last_split_char == '{': flat['.'.join(keys)] = [val]
            elif last_split_char == ',': flat['.'.join(keys)].append(val)
        
        string_char = None
        if len(split[1]):
            if split[1][0] == '\'' or split[1][0] == '\"':
                if len(split[0]):
                    string_char = split[1][0] if split[0][-1] != '\\' else None
                else:
                    string_char = split[1][0]

    bpd = {}

    for k in flat.keys():
        ks = k.split('.')

        ref = bpd
        for ii in range(len(ks) - 1):
            try:
                ref = ref[ks[ii]]
            except KeyError:
                if ks[ii + 1].isdigit():
                    ref[ks[ii]] = []
                    ref = ref[ks[ii]]
                else:
                    ref[ks[ii]] = {}
                    ref = ref[ks[ii]]
            except TypeError:
                try:
                    ref = ref[int(ks[ii])]
                except IndexError:
                    ref.append({})
                    ref = ref[int(ks[ii])]
        ref[ks[-1]] = flat[k]

    return bpd


def _strip_lua_comments(text):
    cleaned = []
    quote = None
    escaped = False
    ii = 0

    while ii < len(text):
        char = text[ii]
        next_char = text[ii + 1] if ii + 1 < len(text) else ''

        if quote:
            cleaned.append(char)
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == quote:
                quote = None
            ii += 1
            continue

        if char in ('"', "'"):
            quote = char
            cleaned.append(char)
            ii += 1
            continue

        if char == '-' and next_char == '-':
            while ii < len(text) and text[ii] not in '\r\n':
                ii += 1
            continue

        if char == '#':
            while ii < len(text) and text[ii] not in '\r\n':
                ii += 1
            continue

        cleaned.append(char)
        ii += 1

    return ''.join(cleaned)


def _find_matching_brace(text, open_index):
    quote = None
    escaped = False
    depth = 0

    for ii in range(open_index, len(text)):
        char = text[ii]

        if quote:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == quote:
                quote = None
            continue

        if char in ('"', "'"):
            quote = char
            continue

        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return ii

    return -1


def _find_named_table(text, name):
    pattern = re.compile(r'(?<![\w])' + re.escape(name) + r'\s*=\s*(?:[A-Za-z_]\w*\s*)?\{')
    match = pattern.search(text)
    if not match:
        return None

    open_index = text.find('{', match.start())
    close_index = _find_matching_brace(text, open_index)
    if close_index == -1:
        return None

    return text[open_index + 1:close_index]


def _iter_top_level_tables(text):
    quote = None
    escaped = False
    depth = 0
    start = None

    for ii, char in enumerate(text):
        if quote:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == quote:
                quote = None
            continue

        if char in ('"', "'"):
            quote = char
            continue

        if char == '{':
            if depth == 0:
                start = ii + 1
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0 and start is not None:
                yield text[start:ii]
                start = None


def _parse_simple_lua_fields(text):
    value_pattern = (
        r"(?P<key>[A-Za-z_]\w*)\s*=\s*"
        r"(?P<value>"
        r"'(?:\\.|[^'])*'"
        r'|"(?:\\.|[^"])*"'
        r'|true|false'
        r'|[-+]?\d+(?:\.\d+)?'
        r")"
    )

    values = {}
    for match in re.finditer(value_pattern, text):
        raw_value = match.group('value')
        if raw_value[0] in ('"', "'"):
            value = raw_value[1:-1]
        elif raw_value in ('true', 'false'):
            value = raw_value == 'true'
        elif '.' in raw_value:
            value = float(raw_value)
        else:
            value = int(raw_value)

        values[match.group('key')] = value

    return values


def read_bp_materials(filepath):
    if not path.isfile(filepath):
        return None

    text = open(filepath, 'rb').read().decode()
    text = _strip_lua_comments(text)

    display = _find_named_table(text, 'Display')
    if not display:
        return None

    mesh = _find_named_table(display, 'Mesh')
    if not mesh:
        return None

    lods = _find_named_table(mesh, 'LODs')
    if not lods:
        return None

    lod_values = [_parse_simple_lua_fields(lod) for lod in _iter_top_level_tables(lods)]
    if not lod_values:
        return None

    return {'Display': {'Mesh': {'LODs': lod_values}}}
