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

![Autonomous Robot Path Simulator in action](screenshot.png)

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

## Academic Viva Notes

- Path planning and motion are modularly separated.
- Pathfinding outputs discrete waypoints; motion converts them to continuous trajectories.
- RK4 integration improves stability/accuracy over Euler integration for smooth robot behavior.
- Dynamic obstacles trigger online replanning from robot current position.
- Visualization separates scene rendering, camera control, and dashboard overlay.
