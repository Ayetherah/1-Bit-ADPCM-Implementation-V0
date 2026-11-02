import struct, sys

# Adaptive step constants (same for encoder and decoder)
INITIAL_STEP = 0.005
GROWTH = 1.1
DECAY = 0.9
MIN_STEP = 0.0001
MAX_STEP = 0.5

INPUT_RAW = sys.argv[1]
OUTPUT_DPCM = sys.argv[2]

def read_f32le(filename):
    with open(filename, 'rb') as f:
        data = f.read()
    return struct.unpack(f'<{len(data)//4}f', data)

def encode_channel(samples):
    pred = 0.0
    step = INITIAL_STEP
    bits = []
    prev_bit = None
    for s in samples:
        diff = s - pred
        if diff >= 0:
            bit = 1
            pred += step
        else:
            bit = 0
            pred -= step
        if prev_bit is not None:
            if bit == prev_bit:
                step = min(step * GROWTH, MAX_STEP)
            else:
                step = max(step * DECAY, MIN_STEP)
        prev_bit = bit
        bits.append(bit)
    return bits

samples = read_f32le(INPUT_RAW)
# interleaved L,R -> split channels
L = samples[0::2]
R = samples[1::2]
num_frames = len(L)

bits_L = encode_channel(L)
bits_R = encode_channel(R)

# interleave: L bit, R bit per frame
interleaved_bits = []
for i in range(num_frames):
    interleaved_bits.append(bits_L[i])
    interleaved_bits.append(bits_R[i])

# pack into bytes MSB first
packed = bytearray()
for i in range(0, len(interleaved_bits), 8):
    chunk = interleaved_bits[i:i+8]
    # pad with zeros if less than 8
    while len(chunk) < 8:
        chunk.append(0)
    byte = 0
    for bit in chunk:
        byte = (byte << 1) | bit
    packed.append(byte)

# write header + packed data
with open(OUTPUT_DPCM, 'wb') as f:
    f.write(b'1dpcm-0ver-192khz-2chan\n')
    f.write(packed)

print(f"Encoded {num_frames} frames, packed into {len(packed)} bytes")
