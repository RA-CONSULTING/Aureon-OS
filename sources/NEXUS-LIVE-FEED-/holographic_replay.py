import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D

def create_holographic_replay(signal_data, target_info):
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    # Unpack target info
    target_position = target_info['position']
    target_radius = target_info['radius']
    target_color = target_info['color']

    # Create a sphere to represent the target
    u = np.linspace(0, 2 * np.pi, 100)
    v = np.linspace(0, np.pi, 100)
    x = target_radius * np.outer(np.cos(u), np.sin(v)) + target_position[0]
    y = target_radius * np.outer(np.sin(u), np.sin(v)) + target_position[1]
    z = target_radius * np.outer(np.ones(np.size(u)), np.cos(v)) + target_position[2]
    ax.plot_surface(x, y, z, color=target_color, alpha=0.3)

    # Prepare for the signal animation
    signal_line, = ax.plot([], [], [], lw=2, color='cyan')

    def init():
        signal_line.set_data([], [])
        signal_line.set_3d_properties([])
        return signal_line,

    def update(frame):
        # Simulate the signal path over time
        x_data = signal_data[:frame, 0]
        y_data = signal_data[:frame, 1]
        z_data = signal_data[:frame, 2]
        signal_line.set_data(x_data, y_data)
        signal_line.set_3d_properties(z_data)
        return signal_line,

    ani = FuncAnimation(fig, update, frames=len(signal_data), init_func=init, blit=True, interval=20)

    # Setting the plot limits and labels
    ax.set_xlim([0, 100])
    ax.set_ylim([0, 100])
    ax.set_zlim([0, 100])
    ax.set_xlabel('X Coordinate')
    ax.set_ylabel('Y Coordinate')
    ax.set_zlabel('Z Coordinate')
    ax.set_title('Holographic Replay of Signal Path')

    plt.show()

if __name__ == '__main__':
    # Example Usage
    # Simulate a signal path spiraling towards a target
    t = np.linspace(0, 10, 500)
    signal_path = np.array([
        50 + 25 * np.cos(t) * np.exp(-t/10),
        50 + 25 * np.sin(t) * np.exp(-t/10),
        t * 10  # Signal rises over time
    ]).T

    target_details = {
        'position': [50, 50, 95],  # Center of the target
        'radius': 5,
        'color': 'red'
    }

    create_holographic_replay(signal_path, target_details)
