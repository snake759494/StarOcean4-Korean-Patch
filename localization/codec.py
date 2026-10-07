"""Lossless text-token export; keep engine controls visible during authoring."""
import re,struct

LATIN={1889+i:str(i) for i in range(10)}
LATIN.update({1949+i:chr(65+i) for i in range(26)})
LATIN.update({1975+i:chr(97+i) for i in range(26)})
LATIN.update(dict(zip(range(1899,1949),[
'™','-','—','+','＋','%','％','/','／',':',':',';',';','.', '.',"'",'"','-','—',',',',',' ',' ','!','#','$','&','(',')','*','<','>','[','{','「','、','。','・','?',']','}','」','\\','^','_','`','|','~','=','@'])))
LATIN.update({2001:'°',2002:'È',2003:'À',2004:'Ù',2005:'Ì',2006:'Ò',2007:'è',2008:'è',2009:'é',2010:'à',2011:'ò',2012:'ì',2013:'ù',2014:'ª',2015:'ä',2016:'ö',2017:'ü',2018:'ß',2019:'Ä',2020:'Ö',2021:'Ü',2022:'„',2023:'“',2024:'â',2025:'ë',2026:'ê',2027:'ô',2028:'ï',2029:'î',2030:'û',2031:'œ',2032:'æ',2033:'Ê',2034:'Ë',2035:'Â',2036:'Û',2037:'Ô',2038:'Î',2039:'Ï',2040:'Æ',2041:'Œ',2042:'Ç',2043:'¿',2044:'º',2045:'á',2046:'í',2047:'ó',2048:'ú',2049:'ñ',2050:'Õ',2051:'õ',2052:'»',2053:'«',2054:'¡',2055:'£',2056:'ã',2057:'å',2058:'ç',2059:'ÿ',2060:'µ',2061:'ø',2062:'Á',2063:'Ã',2064:'Å',2065:'Ñ',2066:'Í',2067:'Ú',2068:'Ó',2069:'Ø',2070:'‹',2071:'›',2072:'Ÿ',2073:'´',2074:'‘',2075:'’',2076:'”',2077:'÷',2078:'¢',2079:'§',2080:'¦',2081:'☆',2082:'★',2083:'♪',2084:'•',2085:'α',2086:'◆',2087:'þ',2088:'ý',2089:'š',2090:'ð',2091:'Þ',2092:'Ý',2093:'Š',2094:'Ð',2095:'×',2096:'¥',2097:'€',2098:'¤'})
# Only the verified digits and letters in the global Japanese bank are known.
LATIN.update({1+i:str(i) for i in range(10)})
LATIN.update({99+i:chr(65+i) for i in range(26)})
LATIN.update({125+i:chr(97+i) for i in range(26)})

TOKEN=re.compile(r'\{(?:RAW:[0-9a-fA-F]+|PAGE|NAME:\d+:[^{}]*|G:\d+)\}')
ENCODING={c:i for i,c in LATIN.items() if i>=1889}
ENCODING.update({' ':1920,'.':1912,'…':97})

def literal_chars(text):
    for part in re.split(r'(\{[^{}]+\})',text):
        if part.startswith('{NAME:'):
            yield from part[1:-1].split(':',2)[2]
        elif part.startswith('{'):
            if not TOKEN.fullmatch(part): raise ValueError(part)
        else: yield from part

def encode(text,mapping):
    def index(n):
        assert 0<n<0x4000
        return bytes([n]) if n<128 else bytes([0x80|(n&127),n>>7])
    out=bytearray()
    for part in re.split(r'(\{[^{}]+\})',text):
        if part=='{PAGE}': out+=b'\x81\x80'
        elif part.startswith('{RAW:'):
            assert TOKEN.fullmatch(part),part
            out+=bytes.fromhex(part[5:-1])
        elif part.startswith('{G:'):
            out+=index(int(part[3:-1]))   # original glyph kept as-is
        elif part.startswith('{NAME:'):
            _,identifier,name=part[1:-1].split(':',2)
            out+=b'\x93\x80'+struct.pack('<H',int(identifier))+encode(name,mapping)
        else:
            assert '{' not in part,part
            for ch in part:
                if ch=='\n': out+=b'\x80\x80'
                else: out+=index(mapping[ch] if ch in mapping else ENCODING[ch])
    return bytes(out)+b'\0'

def decode(raw,local=False):
    out=[]; i=0
    while i<len(raw):
        b=raw[i]
        if b==0: break
        if b<128: value=b; count=1
        else:
            if i+1>=len(raw): out.append('{RAW:'+raw[i:].hex()+'}'); break
            value=(b&127)|(raw[i+1]<<7); count=2
        if value<0x4000:
            out.append(('{G:%d}'%value) if local else LATIN.get(value,'{G:%d}'%value)); i+=count; continue
        if value==0x4000: out.append('\n'); i+=2; continue
        if value==0x4001: out.append('{PAGE}'); i+=2; continue
        # 0x8028 inserts a mapped input icon followed by a 32-bit action ID.
        if b==0xa8 and raw[i+1]==0x80: count=6
        elif b==0x88 and raw[i+1]==0x80: count=3   # help-window style, 1-byte arg
        elif b==0x94 and raw[i+1]==0x80: count=4   # 2-byte arg
        elif b==0x84 and raw[i+1]==0x80: count=3
        elif b==0xac and raw[i+1]==0x80: count=3
        elif b in (0xae,0xaf,0xb1) and raw[i+1]==0x80: count=3   # arena branch codes, 1-byte arg
        elif b in (0xb0,0xb2,0x91) and raw[i+1]==0x80: count=2   # branch end / ruby end
        elif b==0x90 and raw[i+1]==0x80 and raw[i+2:i+4]==b'\x90\x80':
            # ruby: 9080 9080 <reading glyphs> 00 <base glyphs> 9180 ; keep the reading's 00 terminator
            end=raw.find(b'\0',i+4)
            out.append('{RAW:90809080}'+decode(raw[i+4:end],local)+'{RAW:00}'); i=end+1; continue
        elif b==0x93 and raw[i+1]==0x80:
            end=raw.find(b'\0',i+4)
            count=(end+1-i) if end>=0 else len(raw)-i
        elif b not in (0x81,0x82,0x85,0x89):
            # Unknown arity must not silently truncate or misinterpret arguments.
            out.append('{RAW:'+raw[i:].hex()+'}'); break
        out.append('{RAW:'+raw[i:i+count].hex()+'}'); i+=count
    return ''.join(out)

def messages(data):
    sections=struct.unpack_from('<7I',data,0x18)
    count=struct.unpack_from('<I',data,0x3c)[0]
    rows=[struct.unpack_from('<II',data,sections[2]+8*i) for i in range(count)]
    base=sections[3]; end=sections[4] or len(data)
    offsets=sorted({off for _,off in rows}|{end-base})
    bounds=dict(zip(offsets,offsets[1:]))
    return {mid:data[base+off:base+bounds.get(off,end-base)] for mid,off in rows}
