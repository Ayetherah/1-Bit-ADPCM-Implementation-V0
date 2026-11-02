import struct, wave, sys

INITIAL_STEP = 0.005
GROWTH = 1.1
DECAY = 0.9
MIN_STEP = 0.0001
MAX_STEP = 0.5

INPUT_DPCM = sys.argv[1]
OUTPUT_WAV = sys.argv[2]

with open(INPUT_DPCM, 'rb') as f:
    header = f.readline().decode().strip()
    data = f.read()

# verify header
if header != '1dpcm-0ver-192khz-2chan':
    print("Bad header")
    sys.exit(1)

# unpack bits MSB first
bits = []
for byte in data:
    for i in range(7, -1, -1):
        bits.append((byte >> i) & 1)

# split into L and R streams (interleaved per frame)
num_frames = len(bits) // 2   # ignore padding
bits_L = bits[0::2]
bits_R = bits[1::2]

def decode_channel(bitstream):
    pred = 0.0
    step = INITIAL_STEP
    reconstructed = []
    prev_bit = None
    for b in bitstream:
        if b == 1:
            pred += step
        else:
            pred -= step
        reconstructed.append(pred)
        if prev_bit is not None:
            if b == prev_bit:
                step = min(step * GROWTH, MAX_STEP)
            else:
                step = max(step * DECAY, MIN_STEP)
        prev_bit = b
    return reconstructed

L_rec = decode_channel(bits_L)
R_rec = decode_channel(bits_R)

# interleave and clamp
interleaved = []
for i in range(num_frames):
    interleaved.append(max(-1.0, min(1.0, L_rec[i])))
    interleaved.append(max(-1.0, min(1.0, R_rec[i])))

with wave.open(OUTPUT_WAV, 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(192000)
    frames = bytearray()
    for s in interleaved:
        pcm = int(s * 32767)
        frames += struct.pack('<h', pcm)
    w.writeframes(bytes(frames))

print(f"Decoded {num_frames} frames from {len(data)} bytes")
