import docker
import tempfile
import os
from pathlib import Path
import subprocess
import shutil

# Find the Docker executable path once at startup
DOCKER_EXECUTABLE = shutil.which('docker')
if not DOCKER_EXECUTABLE:
    # If docker is not found, we can't proceed, but we'll let main.py's UI/CLI
    # handlers deal with the error more gracefully.
    client = None # Indicate no client available
else:
    # Initialize Docker SDK client
    client = docker.from_env()

def find_terminal():
    """Finds an available terminal emulator."""
    # Pairs of (terminal_command, execute_flag)
    terminals = [
        ('x-terminal-emulator', '-e'),
        ('gnome-terminal', '--'),
        ('konsole', '-e'),
        ('xfce4-terminal', '-e'),
        ('xterm', '-e'),
    ]
    for term, flag in terminals:
        if shutil.which(term):
            return term, flag
    return None, None

def build_image(tag, base_image, install_commands, log_callback=print, nocache=False):
    """
    Builds a Docker image and streams logs.
    Yields log lines as they are received.
    """
    if not DOCKER_EXECUTABLE or not client:
        log_callback("ERROR: Docker is not accessible. Please ensure Docker is installed and running.")
        return None

    dockerfile_content = [f"FROM {base_image}"]
    dockerfile_content.extend([f"RUN {cmd}" for cmd in install_commands if cmd.strip()])
    
    with tempfile.TemporaryDirectory() as tmpdir:
        dockerfile_path = Path(tmpdir) / "Dockerfile"
        with open(dockerfile_path, "w") as f:
            f.write("\n".join(dockerfile_content))
            
        log_callback("--- Dockerfile Generated ---")
        log_callback("\n".join(dockerfile_content))
        log_callback("--------------------------")
        log_callback(f"Building image: {tag} {'(no-cache)' if nocache else ''}...")

        try:
            # Check for existing container and remove it
            try:
                existing_container = client.containers.get(tag)
                log_callback(f"Removing existing container named '{tag}'...")
                existing_container.remove(force=True)
            except docker.errors.NotFound:
                pass # No container with that name exists

            image, logs = client.images.build(path=tmpdir, tag=tag, rm=True, nocache=nocache)
            for chunk in logs:
                if 'stream' in chunk:
                    for line in chunk['stream'].splitlines():
                        log_callback(line)
            log_callback(f"Image {image.short_id} built successfully.")
            return image
        except docker.errors.BuildError as e:
            log_callback("--- BUILD FAILED ---")
            for chunk in e.build_log:
                 if 'stream' in chunk:
                    for line in chunk['stream'].splitlines():
                        log_callback(line)
            return None
        except docker.errors.APIError as e:
            log_callback(f"--- DOCKER API ERROR ---")
            log_callback(str(e))
            return None


def run_container(image_tag, container_name, run_command, mode, 
                    volumes=None, log_callback=print):
    """Runs a container with the specified options."""
    if not DOCKER_EXECUTABLE or not client:
        log_callback("ERROR: Docker is not accessible. Please ensure Docker is installed and running.")
        return None

    if volumes is None:
        volumes = []

    try:
        # Check for existing container and remove it
        try:
            existing_container = client.containers.get(container_name)
            log_callback(f"Removing existing container named '{container_name}'...")
            existing_container.remove(force=True)
        except docker.errors.NotFound:
            pass # No container with that name exists
            
        # --- Prepare Volume Mounts ---
        volume_mount_args = []
        volumes_sdk = {}
        first_volume_container_path = None

        for vol_map in volumes:
            host_path = vol_map['host']
            container_path = vol_map['container']
            if host_path and container_path:
                log_callback(f"Mounting volume: '{host_path}' -> '{container_path}'")
                volume_mount_args.extend(['-v', f'{host_path}:{container_path}'])
                volumes_sdk[host_path] = {'bind': container_path, 'mode': 'rw'}
                if first_volume_container_path is None:
                    first_volume_container_path = container_path

        # --- Prepare Working Directory ---
        working_dir_arg = []
        if first_volume_container_path:
            log_callback(f"Setting working directory inside container to: '{first_volume_container_path}'")
            working_dir_arg = ['-w', first_volume_container_path]

        # --- Base command for subprocess calls ---
        docker_run_cmd_base = [
            DOCKER_EXECUTABLE, 'run', '--rm', # --rm is good for interactive/gui apps
            '--name', container_name
        ] + volume_mount_args + working_dir_arg

        if mode == 'terminal':
            log_callback("Searching for available terminal...")
            terminal_cmd, exec_flag = find_terminal()

            if not terminal_cmd:
                log_callback("--- ERROR ---")
                log_callback("No terminal emulator found. Please install one of 'gnome-terminal', 'konsole', 'xfce4-terminal', or 'xterm'.")
                return None

            log_callback(f"Found terminal: {terminal_cmd}")
            log_callback(f"Starting container '{container_name}' in a new terminal...")
            
            # Prepare run_command for execution
            final_run_command_parts = []
            if run_command:
                # If command is not bash or sh, wrap it in bash -c
                if run_command.strip() not in ["bash", "sh"]:
                    final_run_command_parts.extend(["bash", "-c", run_command])
                else:
                    final_run_command_parts.append(run_command)
            
            # Construct the Docker command list that will be executed by the terminal
            docker_exec_command_list = docker_run_cmd_base + ['-it', image_tag]
            if final_run_command_parts:
                docker_exec_command_list.extend(final_run_command_parts)
            
            # Create a clean environment for the subprocess
            clean_env = os.environ.copy()
            for var in ['LD_LIBRARY_PATH', 'QT_PLUGIN_PATH', 'QML2_IMPORT_PATH']:
                if var in clean_env:
                    del clean_env[var]
            
            # Now, wrap this Docker command for the specific terminal emulator
            if exec_flag == '--':
                 # For terminals like gnome-terminal, they expect '--' followed by the command parts
                 cmd = [terminal_cmd, exec_flag] + docker_exec_command_list
            else: # for '-e' style (xterm, konsole, xfce4-terminal)
                # These terminals typically expect the command to execute as a single string argument to -e
                # So we join the docker command parts into a single string
                cmd = [terminal_cmd, exec_flag, " ".join(docker_exec_command_list)]

            subprocess.Popen(cmd, env=clean_env) # Pass the cleaned environment
            log_callback("Terminal launched.")
            return True
            
        elif mode == 'background':
            log_callback(f"Starting container '{container_name}' in the background...")
            # For background, --rm is not desirable, so we rebuild the command
            # Also need to pass working_dir for SDK call
            container = client.containers.run(
                image_tag,
                command=run_command,
                name=container_name,
                volumes=volumes_sdk,
                working_dir=first_volume_container_path if first_volume_container_path else None,
                detach=True
            )
            log_callback(f"Container {container.short_id} started in background.")
            return container

        elif mode == 'gui_app':
            log_callback(f"Starting GUI application '{container_name}'...")
            
            xauth_path = os.environ.get('XAUTHORITY', str(Path.home() / '.Xauthority'))
            if not os.path.exists(xauth_path):
                log_callback("--- X11 Auth Warning ---")
                log_callback(f"No .Xauthority file found at '{xauth_path}'.")
                log_callback("If the GUI app fails to start, you may need to run `xhost +local:docker` on your host.")
                xauth_mount = []
            else:
                xauth_mount = ['-v', f'{xauth_path}:/root/.Xauthority:rw', '-e', 'XAUTHORITY=/root/.Xauthority']

            docker_cmd = docker_run_cmd_base + [
                '-e', 'DISPLAY=' + os.environ.get('DISPLAY', ':0'),
                '-v', '/tmp/.X11-unix:/tmp/.X11-unix',
            ] + xauth_mount + [image_tag]
            
            if run_command:
                docker_cmd.extend(run_command.split())
            
            # Create a clean environment for the subprocess
            clean_env = os.environ.copy()
            for var in ['LD_LIBRARY_PATH', 'QT_PLUGIN_PATH', 'QML2_IMPORT_PATH']:
                if var in clean_env:
                    del clean_env[var]

            log_callback(f"Executing: {' '.join(docker_cmd)}")
            subprocess.Popen(docker_cmd, env=clean_env) # Pass the cleaned environment
            log_callback("GUI application launched.")
            return True


    except docker.errors.APIError as e:
        log_callback(f"--- DOCKER API ERROR ---")
        log_callback(str(e))
        return None
    except FileNotFoundError:
        # This will now primarily catch if 'docker' itself is not found
        log_callback("--- ERROR ---")
        log_callback("Docker command not found or accessible. Ensure Docker is installed and in your PATH.")
        return None
