
import os
from PIL import Image

frame_dir = "reel_frames"
output_gif_path = "experience_reel.gif"

# Get a sorted list of all frame images
frame_files = sorted([f for f in os.listdir(frame_dir) if f.endswith(".png")])

if not frame_files:
    print("Error: No frames found in the 'reel_frames' directory.")
else:
    # Create a list of PIL Image objects
    frames = [Image.open(os.path.join(frame_dir, f)) for f in frame_files]

    # Save as an animated GIF
    frames[0].save(
        output_gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=50,  # 1000ms / 20fps = 50ms per frame
        loop=0  # Loop indefinitely
    )

    print(f"Experience Reel saved as an animated GIF: {output_gif_path}")
