# Autonomous Robot Path Simulation

A Python 3D simulator for autonomous navigation in dynamic environments, featuring:

- A*, Dijkstra, and BFS path planning
- Interactive map editing (start, goal, obstacles)
- Dynamic moving obstacles with real-time replanning
- Smooth ODE-based robot motion using RK4 integration
- Modern OpenGL visualization with glow effects and animated path rendering
- Dashboard with metrics, speed control, and algorithm comparison chart
- Save/load map support
- Optional ROS2 bridge module for future real-robot integration

## Screenshot

<img width="1548" height="888" alt="image" src="https://github.com/user-attachments/assets/84361333-d008-4e43-840e-92423cb455ce" />
<img width="1048" height="610" alt="image" src="https://github.com/user-attachments/assets/9fac27e0-40e6-4e6c-ae89-eb18b049e38e" />



*The simulator running with A* pathfinding. The blue tiles show the computed path from the green start marker (lower left) to the red goal marker (upper right). Purple obstacles block the grid; the robot will move smoothly along the blue path when Start Sim is pressed.*

## Project Structure

- `main.py`: Application entry point and simulation loop
- `pathfinding/`: A*, Dijkstra, BFS implementations
- `motion/`: ODE and RK4 motion control
- `visualization/`: OpenGL renderer and camera
- `ui/`: Dashboard and controls
- `utils/`: Grid model, configuration, map I/O
- `ros_integration/`: Optional ROS2 state publisher bridge

## Requirements

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Run

```powershell
python main.py
```

## Controls

### Mouse
- Left click (on grid): place using selected tool
- Left drag (on grid): paint obstacles/erase continuously
- Right drag: orbit camera
- Middle drag: pan camera
- Scroll: zoom

### Keyboard
- `1`: A*
- `2`: Dijkstra
- `3`: BFS
- `Space`: Pause/Resume
- `R`: Reset
- `F`: Toggle follow camera
- `D`: Toggle dynamic obstacles
- `C`: Compare all algorithms
- `S`: Save map to `maps/default_map.json`
- `L`: Load map from `maps/default_map.json`
- `Esc`: Quit

## ROS Integration (Optional)

The simulator includes a non-blocking ROS bridge in `ros_integration/ros_bridge.py`.

To enable it:

1. Install ROS2 Python packages in your ROS environment.
2. Set `ENABLE_ROS_BRIDGE = True` in `utils/config.py`.
3. Run the simulation from a ROS-sourced shell.

Published topic:

- `/sim/state` (`std_msgs/String`) with state, robot position, and metrics.
Author
Avi Sharma
