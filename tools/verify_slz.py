"""Strict SLZ v1/v3 decoder matching native zero-distance termination."""
import struct

def decode_native_slz(buf):
    assert buf[:3] == b'SLZ' and buf[3] in (1,3)
    unit=2 if buf[3]==3 else 1
    csize, usize = struct.unpack_from('<II', buf, 8)
    pos = struct.unpack_from('<I', buf, 20)[0]
    limit = pos + csize
    chunk_size = buf[25] << 10
    out = bytearray()
    chunks = []
    while len(out) < usize:
        clen = struct.unpack_from('<H', buf, pos)[0]; pos += 2
        count = min(chunk_size, usize-len(out))
        if clen == 0 or clen == count:
            out += buf[pos:pos+count]; pos += count
            chunks.append({'stored': True, 'size': count})
            continue
        end = pos + clen
        base = len(out)
        flags = bits = 0
        while True:
            if bits == 0:
                assert pos+unit <= end, 'missing terminator/flags'
                flags = int.from_bytes(buf[pos:pos+unit],'little'); pos += unit; bits=unit*8
            literal = flags & 1; flags >>= 1; bits -= 1
            if literal:
                assert pos+unit<=end, 'truncated literal'
                out+=buf[pos:pos+unit]; pos+=unit
            else:
                assert pos+2<=end, 'missing zero-distance terminator'
                token=struct.unpack_from('<H',buf,pos)[0]; pos+=2
                distance = (token & 4095)*unit
                if distance == 0: break
                assert distance <= len(out)-base, 'invalid distance'
                for _ in range((token >> 12)+(2 if unit==2 else 3)):
                    src = len(out)-distance
                    out += out[src:src+unit]
            assert len(out)-base <= count, 'native output buffer overrun'
        assert len(out)-base == count
        assert pos <= end
        pos = end
        chunks.append({'stored':False,'size':count})
    assert pos == limit, (pos,limit)
    return bytes(out), chunks

decode_native_v3=decode_native_slz  # Compatibility with earlier project scripts.

if __name__ == '__main__':
    import random
    from slzenc import slz_compress_v3,slz_compress
    rng=random.Random(4096)
    for n in [2,32,34,64,65534,65536,65538,131072]:
        for data in [bytes(n),rng.randbytes(n),(b'ABCD'*((n+3)//4))[:n]]:
            assert decode_native_v3(slz_compress_v3(data))[0] == data
            assert decode_native_slz(slz_compress(data))[0] == data
    print('48 strict native-semantics v1/v3 round trips passed (including 64 KiB stored chunks).')
