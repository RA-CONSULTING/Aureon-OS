
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import os

class FoveatedRenderer:
    def __init__(self, screen_res=(512, 512)):
        self.screen_res = screen_res
        self.low_res_factor = 16

    def create_scene(self):
        x = np.linspace(-1, 1, self.screen_res[0])
        y = np.linspace(-1, 1, self.screen_res[1])
        xv, yv = np.meshgrid(x, y)
        
        scene = np.sin(xv * 10) * np.cos(yv * 10) + np.sin(xv * 20)
        scene = (scene - np.min(scene)) / (np.max(scene) - np.min(scene))

        color_scene = np.zeros((*self.screen_res, 3), dtype=np.float32)
        color_scene[..., 0] = np.clip(scene * 1.2, 0, 1)
        color_scene[..., 1] = np.clip(scene * 0.8, 0, 1)
        color_scene[..., 2] = np.clip(1.0 - scene, 0, 1)

        # Add a circular object
        cy, cx = self.screen_res[0] // 2, self.screen_res[1] // 2
        radius = self.screen_res[0] // 8
        y_grid, x_grid = np.ogrid[:self.screen_res[0], :self.screen_res[1]]
        mask = (x_grid - cx)**2 + (y_grid - cy)**2 < radius**2
        color_scene[mask] = [1.0, 1.0, 0.9]

        return (color_scene * 255).astype(np.uint8)

    def render(self, gaze_point, scene):
        (h, w, _) = scene.shape
        low_res_h, low_res_w = h // self.low_res_factor, w // self.low_res_factor
        
        # Use PIL for resizing to avoid OpenCV
        pil_scene = Image.fromarray(scene)
        peripheral = pil_scene.resize((low_res_w, low_res_h), Image.NEAREST)
        peripheral = peripheral.resize((w, h), Image.NEAREST)
        peripheral = np.array(peripheral)

        fovea_radius = h // 5
        y_grid, x_grid = np.ogrid[:h, :w]
        dist_from_gaze = np.sqrt((x_grid - gaze_point[0])**2 + (y_grid - gaze_point[1])**2)
        
        mask = 1.0 - np.clip(dist_from_gaze / fovea_radius, 0, 1)
        mask = mask**2
        mask_3d = np.repeat(mask[:, :, np.newaxis], 3, axis=2)
        
        composited = scene * mask_3d + peripheral * (1 - mask_3d)
        return composited.astype(np.uint8)

class AdvancedSLMHolography:
    def __init__(self, resolution=(512, 512), wavelength=532e-9, pixel_pitch=8e-6):
        self.resolution = resolution
        self.wavelength = wavelength
        self.pixel_pitch = pixel_pitch

    def generate_phase_hologram(self, image_path):
        img = Image.open(image_path).convert('L').resize(self.resolution)
        target_amplitude = np.array(img) / 255.0
        random_phase = np.random.uniform(0, 2 * np.pi, self.resolution)
        object_field = target_amplitude * np.exp(1j * random_phase)
        hologram_field = np.fft.ifft2(object_field)
        return np.angle(hologram_field)

    def propagate_fresnel(self, phase_hologram, propagation_distance):
        fx = np.fft.fftfreq(self.resolution[0], self.pixel_pitch)
        fy = np.fft.fftfreq(self.resolution[1], self.pixel_pitch)
        FX, FY = np.meshgrid(fx, fy)
        kernel_fft = np.exp(-1j * np.pi * self.wavelength * propagation_distance * (FX**2 + FY**2))
        hologram_field = np.exp(1j * phase_hologram)
        reconstructed_field_fft = np.fft.fft2(hologram_field) * kernel_fft
        reconstructed_field = np.fft.ifft2(reconstructed_field_fft)
        intensity = np.abs(reconstructed_field)**2
        return intensity

def add_text_to_frame(frame, text):
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 20)
    except IOError:
        font = ImageFont.load_default()
    draw.text((15, 15), text, fill=(255, 255, 255), font=font)
    return np.array(img)

def main():
    frame_dir = "reel_frames"
    os.makedirs(frame_dir, exist_ok=True)
    frame_count = 0

    renderer = FoveatedRenderer(screen_res=(512, 512))
    scene = renderer.create_scene()
    scene_frame = add_text_to_frame(scene.copy(), "1. Synthetic Scene")
    for _ in range(40):
        Image.fromarray(scene_frame).save(f"{frame_dir}/frame_{frame_count:04d}.png")
        frame_count += 1

    num_gaze_frames = 80
    gaze_path_x = (256 + 180 * np.cos(np.linspace(0, 2*np.pi, num_gaze_frames))).astype(int)
    gaze_path_y = (256 + 180 * np.sin(np.linspace(0, 4*np.pi, num_gaze_frames))).astype(int)
    
    for i in range(num_gaze_frames):
        foveated_frame = renderer.render((gaze_path_x[i], gaze_path_y[i]), scene)
        foveated_frame = add_text_to_frame(foveated_frame, "2. Foveated Rendering")
        Image.fromarray(foveated_frame).save(f"{frame_dir}/frame_{frame_count:04d}.png")
        frame_count += 1

    holo_sim = AdvancedSLMHolography(resolution=(512, 512))
    target_image_path = "target_square.png"
    if not os.path.exists(target_image_path):
        img_array = np.zeros((512,512)); img_array[192:320, 192:320] = 1.0
        Image.fromarray((img_array * 255).astype(np.uint8)).save(target_image_path)
    
    phase_pattern = holo_sim.generate_phase_hologram(target_image_path)
    phase_frame = (phase_pattern - np.min(phase_pattern)) / (np.max(phase_pattern) - np.min(phase_pattern))
    phase_frame_rgb = (plt.get_cmap('twilight_shifted')(phase_frame)[:,:,:3] * 255).astype(np.uint8)
    phase_frame_text = add_text_to_frame(phase_frame_rgb, "3. SLM Phase Hologram")
    for _ in range(40):
        Image.fromarray(phase_frame_text).save(f"{frame_dir}/frame_{frame_count:04d}.png")
        frame_count += 1

    num_replay_frames = 100
    distances = np.concatenate([np.linspace(0.05, 0.25, num_replay_frames // 2), np.linspace(0.25, 0.05, num_replay_frames // 2)])

    for dist in distances:
        replay = holo_sim.propagate_fresnel(phase_pattern, dist)
        replay_norm = np.clip(replay / np.percentile(replay, 99.9), 0, 1)
        replay_rgb = (plt.get_cmap('magma')(replay_norm)[:,:,:3] * 255).astype(np.uint8)
        replay_frame_text = add_text_to_frame(replay_rgb, f"4. Holographic Replay (z={dist:.2f}m)")
        Image.fromarray(replay_frame_text).save(f"{frame_dir}/frame_{frame_count:04d}.png")
        frame_count += 1

    print(f"Generated {frame_count} frames in {frame_dir}")

if __name__ == "__main__":
    main()
