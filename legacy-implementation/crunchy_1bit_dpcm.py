import struct, wave, sys

# Tuning knobs for the adaptive step
INITIAL_STEP = 0.005
GROWTH_FACTOR = 1.1   # when bits repeat
DECAY_FACTOR = 0.9    # when bits alternate
MIN_STEP = 0.0001
MAX_STEP = 0.5

INPUT_RAW = sys.argv[1]
OUTPUT_WAV = sys.argv[2]

def read_f32_raw(filename):
    with open(filename, 'rb') as f:
        data = f.read()
    return struct.unpack(f'<{len(data)//4}f', data)

def write_wav(filename, samples, sample_rate, channels):
    with wave.open(filename, 'wb') as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        frames = bytearray()
        for s in samples:
            si = max(-1.0, min(1.0, s))
            pcm = int(si * 32767)
            frames += struct.pack('<h', pcm)
        w.writeframes(bytes(frames))

def process_channel_adaptive(samples):
    pred = 0.0
    step = INITIAL_STEP
    bits = []
    reconstructed = []
    prev_bit = None

    for s in samples:
        diff = s - pred
        if diff >= 0:
            bit = 1
            pred += step
        else:
            bit = 0
            pred -= step

        # adapt step
        if prev_bit is None:
            # keep step for first sample
            pass
        elif bit == prev_bit:
            step = min(step * GROWTH_FACTOR, MAX_STEP)
        else:
            step = max(step * DECAY_FACTOR, MIN_STEP)

        prev_bit = bit
        bits.append(bit)
        reconstructed.append(pred)

    return bits, reconstructed

# Parameters - hardcoded for quick test
sample_rate = 192000
channels = 2

all_samples = read_f32_raw(INPUT_RAW)
num_frames = len(all_samples) // channels
ch_left = all_samples[0::channels]
ch_right = all_samples[1::channels]

bits_L, rec_L = process_channel_adaptive(ch_left)
bits_R, rec_R = process_channel_adaptive(ch_right)

interleaved = []
for i in range(num_frames):
    interleaved.append(rec_L[i])
    interleaved.append(rec_R[i])

write_wav(OUTPUT_WAV, interleaved, sample_rate, channels)

print(f"Processed {num_frames} frames")
print(f"Bits L+R: {len(bits_L)+len(bits_R)}")
