"""
Implementation of the Lempel–Ziv–Storer–Szymanski algorithm, ported from the
C implementation by Haruhiko Okumura
https://oku.edu.mie-u.ac.jp/~okumura/compression/lzss.c
Public Domain

python version pulled from github user 'nucular'
https://gist.github.com/nucular/258d544bbd1ba401232ae83a11bd8857
"""


class LZSSBase(object):
    def __init__(
        self, infile, outfile, EI=10, EJ=6, P=2, N=0, F=0, rless=0, init_chr=b" "
    ):
        self.infile = infile
        self.outfile = outfile

        self.EI = EI
        self.EJ = EJ
        self.P = P
        self.N = N or (1 << self.EI)
        self.F = F or ((1 << self.EJ) + 1)

        self.rless = 0
        if isinstance(init_chr, int):
            self.init_chr = init_chr
        else:
            self.init_chr = init_chr[0]

        self.buffer = bytearray(self.N * 2)


class LZSSEncoder(LZSSBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bit_buffer = 0
        self.bit_mask = 128
        self.codecount = 0
        self.textcount = 0

    def putbit1(self):
        self.bit_buffer |= self.bit_mask
        self.bit_mask >>= 1
        if self.bit_mask == 0:
            self.outfile.write(bytes((self.bit_buffer,)))
            self.bit_buffer = 0
            self.bit_mask = 128
            self.codecount += 1

    def putbit0(self):
        self.bit_mask >>= 1
        if self.bit_mask == 0:
            self.outfile.write(bytes((self.bit_buffer,)))
            self.bit_buffer = 0
            self.bit_mask = 128
            self.codecount += 1

    def flush_bit_buffer(self):
        if self.bit_mask != 128:
            self.outfile.write(bytes((self.bit_buffer,)))
            self.codecount += 1

    def output1(self, c):
        self.putbit1()
        mask = 256
        mask >>= 1
        while mask:
            if c & mask:
                self.putbit1()
            else:
                self.putbit0()
            mask >>= 1

    def output2(self, x, y):
        self.putbit0()
        mask = self.N >> 1
        while mask:
            if x & mask:
                self.putbit1()
            else:
                self.putbit0()
            mask >>= 1
        mask = (1 << self.EJ) >> 1
        while mask:
            if y & mask:
                self.putbit1()
            else:
                self.putbit0()
            mask >>= 1

    def encode(self):
        for i in range(0, self.N - self.F):
            self.buffer[i] = self.init_chr
        for i in range(self.N - self.F, self.N * 2):
            bufferend = i
            z = self.infile.read(1)
            if len(z) == 0:
                break
            self.buffer[i] = z[0]
            self.textcount += 1
        r = self.N - self.F
        s = 0
        while r < bufferend:
            f1 = min(self.F, bufferend - r)
            x = 0
            y = 1
            c = self.buffer[r]
            for i in range(r - 1, s - 1, -1):
                if self.buffer[i] == c:
                    for j in range(1, f1):
                        if self.buffer[i + j] != self.buffer[r + j]:
                            break
                    if j > y:
                        x = i
                        y = j
            if y <= self.P:
                y = 1
                self.output1(c)
            else:
                self.output2(x & (self.N - 1), y - 2)
            r += y
            s += y
            if r >= self.N * 2 - self.F:
                for i in range(0, self.N):
                    self.buffer[i] = self.buffer[i + self.N]
                bufferend -= self.N
                r -= self.N
                s -= self.N
                while bufferend < self.N * 2:
                    z = self.infile.read(1)
                    if len(z) == 0:
                        break
                    c = z[0]
                    self.buffer[bufferend] = c
                    bufferend += 1
                    self.textcount += 1
        self.flush_bit_buffer()
        return self.textcount, self.codecount


class LZSSDecoder(LZSSBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bit_buffer = 0
        self.bit_mask = 0

    def getbit(self, n):
        x = 0
        for i in range(0, n):
            if self.bit_mask == 0:
                z = self.infile.read(1)
                if len(z) == 0:
                    return None
                self.bit_buffer = z[0]
                self.bit_mask = 128
            x <<= 1
            if self.bit_buffer & self.bit_mask:
                x += 1
            self.bit_mask >>= 1
        return x

    def decode(self):
        for i in range(0, self.N - self.F):
            self.buffer[i] = self.init_chr
        r = (self.N - self.F) - self.rless
        while True:
            c = self.getbit(1)
            if c == None:
                break
            if c:
                c = self.getbit(8)
                if c == None:
                    break
                self.outfile.write(bytes((c,)))
                self.buffer[r] = c
                r = (r + 1) & (self.N - 1)
            else:
                i = self.getbit(self.EI)
                if i == None:
                    break
                j = self.getbit(self.EJ)
                if j == None:
                    break
                for k in range(0, j + 2):
                    c = self.buffer[(i + k) & (self.N - 1)]
                    self.outfile.write(bytes((c,)))
                    self.buffer[r] = c
                    r = (r + 1) & (self.N - 1)


def encode(*args, **kwargs):
    encoder = LZSSEncoder(*args, **kwargs)
    return encoder.encode()


def decode(*args, **kwargs):
    decoder = LZSSDecoder(*args, **kwargs)
    return decoder.decode()
