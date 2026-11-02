#!/usr/bin/env python3
import argparse
import os
import struct
import subprocess
import sys

# Adaptive step constants (same for encoder and decoder)
INITIAL_STEP = 0.005
GROWTH = 1.1
DECAY = 0.9
MIN_STEP = 0.0001
MAX_STEP = 0.5

def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: ffmpeg is not installed or not in your PATH.", file=sys.stderr)
        print("Please install ffmpeg to use this encoder.", file=sys.stderr)
        sys.exit(1)

def encode_to_1dpcm(input_path, output_path):
    # ffmpeg command: decode input, force 192kHz stereo float32, pipe to stdout
    ffmpeg_cmd = [
        "ffmpeg",
        "-i", input_path,
        "-f", "f32le",
        "-acodec", "pcm_f32le",
        "-ac", "2",          # Force Stereo
        "-ar", "192000",     # Force 192 kHz
        "-"                  # Output to stdout
    ]

    print(f"Decoding '{input_path}' via ffmpeg to 192kHz Stereo...")
    
    # Start ffmpeg process
    process = subprocess.Popen(
        ffmpeg_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, # Hide the massive ffmpeg banner
        bufsize=10**8
    )

    pred = [0.0, 0.0]
    step = [INITIAL_STEP, INITIAL_STEP]
    prev_bit = [None, None]
    
    packed_data = bytearray()
    current_byte = 0
    bit_count = 0
    
    total_frames = 0

    # Read from ffmpeg in chunks (e.g., 1 second of audio)
    # 192000 frames * 2 channels * 4 bytes (float32) = 1,536,000 bytes
    chunk_size = 192000 * 2 * 4
    ch = 0 # 0 for Left, 1 for Right

    try:
        while True:
            raw_chunk = process.stdout.read(chunk_size)
            if not raw_chunk:
                break

            # Unpack float32 array
            num_floats = len(raw_chunk) // 4
            if num_floats == 0:
                continue
                
            samples = struct.unpack(f'<{num_floats}f', raw_chunk)

            for s in samples:
                # ADPCM Encoding
                diff = s - pred[ch]
                if diff >= 0:
                    bit = 1
                    pred[ch] += step[ch]
                else:
                    bit = 0
                    pred[ch] -= step[ch]
                
                # Step size adaptation
                if prev_bit[ch] is not None:
                    if bit == prev_bit[ch]:
                        step[ch] = min(step[ch] * GROWTH, MAX_STEP)
                    else:
                        step[ch] = max(step[ch] * DECAY, MIN_STEP)
                prev_bit[ch] = bit

                # Pack bit (MSB first)
                current_byte = (current_byte << 1) | bit
                bit_count += 1

                if bit_count == 8:
                    packed_data.append(current_byte)
                    current_byte = 0
                    bit_count = 0
                
                # Toggle channel
                ch ^= 1
                if ch == 0:
                    total_frames += 1

        # Pad the final byte with zeros if it wasn't exactly 8 bits
        if bit_count > 0:
            current_byte <<= (8 - bit_count)
            packed_data.append(current_byte)

        process.wait()
        if process.returncode != 0:
            print("Error: ffmpeg failed to process the input file.", file=sys.stderr)
            sys.exit(1)

        # Write the final file
        print(f"Writing '{output_path}'...")
        with open(output_path, 'wb') as f:
            f.write(b'1dpcm-0ver-192khz-2chan\n')
            f.write(packed_data)

        print(f"Success! Encoded {total_frames:,} frames into {len(packed_data):,} bytes.")

    except KeyboardInterrupt:
        process.kill()
        print("\nAborted.")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Encode audio into 1dpcm format.")
    parser.add_argument("input", help="Input audio file (WAV, MP3, etc.)")
    parser.add_argument("output", help="Output .1dpcm file")
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"Error: Input file '{args.input}' not found.", file=sys.stderr)
        sys.exit(1)

    check_ffmpeg()
    encode_to_1dpcm(args.input, args.output)

if __name__ == "__main__":
    main()
