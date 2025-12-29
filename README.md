# Docker App Builder

 A simple desktop application for Linux to define, build, and run Docker containers securely for agents like gemini-cli or qwencode as well as GUI apps in their own containers
 
## Prerequisites

- Python 3.9+
- `python3-venv` package (or equivalent for your distribution)
- Docker Engine (must be installed and running)

## Setup

1.  **Clone the repository (or download the source code).**

2.  **Create and activate a Python virtual environment:**
    ```bash
    python3 -m venv venv
    ```

3.  **Install the required dependencies:**
    ```bash
    ./venv/bin/pip install PyQt6 docker
    ```

## Building an Executable

You can create a standalone executable for the Docker App Builder using the provided `build.sh` script. This allows you to run the application on systems that don't have Python or its dependencies installed.

1.  **Make the build script executable (if not already):**
    ```bash
    chmod +x build.sh
    ```
2.  **Run the build script:**
    ```bash
    ./build.sh
    ```
    This process will install PyInstaller (if not already present), clean up previous build artifacts, and then package the application.
3.  **Run the executable:**
    Once the build is complete, you will find the `DockerAppBuilder` executable in the `dist/` directory.
    ```bash
    ./dist/DockerAppBuilder
    ```
    You can then run this executable directly.

## How to Run (GUI)

To launch the graphical interface, run the script with no arguments:
```bash
./venv/bin/python3 docker_app_builder/main.py
```

## How to Use (GUI)

1.  **Fill out the form:**
    -   **Container Name:** A unique name for your container (e.g., `my-test-app`).
    -   **Base Image:** The Docker image to build upon (e.g., `ubuntu:22.04`).
    -   **Installation Commands:** A list of shell commands for the build.
    -   **Run Command:** The command to execute when the container starts.
    -   **Volume Mounts (Optional):** Add multiple volumes by specifying a **Host Path** on your computer and a **Container Path** inside the Docker container. If any volumes are mounted, the **Run Command** will execute from within the *first* mounted volume's directory inside the container by default.
    -   **Run Mode:** Choose `Terminal` for CLI apps, `Background` for services, or `GUI App` for graphical applications.

2.  **Create:**
    -   Click the **Create & Run** button to build the image, save the configuration, and run the container.

3.  **Load and Run Existing Configs:**
    -   Previously created configurations are listed on the right.
    -   Click a configuration name to load its settings.
    -   Click the **Run** button to launch a container using the loaded settings. An existing container with the same name will be removed first.

**Note for GUI Apps:**
If you choose `GUI App` mode, the application will attempt to forward your X11 socket and `.Xauthority` file automatically. In some environments, you may still need to manually grant permission by running `xhost +local:docker` on your host.

## Command-Line Usage (CLI)

You can also create and run containers directly from the command line.

### Examples

#### 1. Installing and Running `gemini-cli`

This example shows how to create a container with Node.js and the `@google/gemini-cli` installed. A volume is mounted to persist the `gemini-cli` configuration.

```bash
./venv/bin/python3 docker_app_builder/main.py create --name gemini-cli-app \
--base-image "ubuntu:22.04" \
--install-commands "apt-get update" \
"apt-get install -y --no-install-recommends curl ca-certificates gnupg" \
"curl -fsSL https://deb.nodesource.com/setup_20.x | bash -" \
"apt-get install -y --no-install-recommends nodejs" \
"npm install -g @google/gemini-cli" \
--run-command "bash" \
--volume "$HOME/.gemini:/root/.gemini" \
--mode terminal \
--run
```

**Explanation:**
- `apt-get` commands install prerequisites for Node.js.
- Node.js is installed from `nodesource`.
- `gemini-cli` is installed globally via `npm`.
- `run-command "bash"` provides an interactive shell upon container launch.
- `--volume "$HOME/.gemini:/root/.gemini"` mounts your host's `.gemini` config directory to the container's root user's `.gemini` directory, ensuring CLI configurations (like `gemini configure`) persist.

To run this saved configuration later:
```bash
./venv/bin/python3 docker_app_builder/main.py run gemini-cli-app
```

#### 2. Installing and Running `qwen-code`

This example shows how to create a container with Node.js and the `qwen-code` CLI agent installed. A volume is mounted to persist its configuration.

```bash
./venv/bin/python3 docker_app_builder/main.py create --name qwen-code-app \
--base-image "ubuntu:22.04" \
--install-commands "apt-get update" \
"apt-get install -y --no-install-recommends curl ca-certificates gnupg" \
"curl -fsSL https://deb.nodesource.com/setup_20.x | bash -" \
"apt-get install -y --no-install-recommends nodejs" \
"npm install -g @qwen-code/qwen-code@latest" \
--run-command "qwen" \
--volume "$HOME/.qwen:/root/.qwen" \
--mode terminal \
--run
```

**Explanation:**
- Similar to `gemini-cli`, prerequisites for Node.js are installed.
- `qwen-code` is installed globally via `npm`.
- `run-command "qwen"` starts the interactive `qwen-code` agent.
- `--volume "$HOME/.qwen:/root/.qwen"` mounts your host's `.qwen` config directory to the container's root user's `.qwen` directory, ensuring `qwen-code` configurations (like authentication tokens) persist.

To run this saved configuration later:
```bash
./venv/bin/python3 docker_app_builder/main.py run qwen-code-app
```

### Create a Configuration

```bash
./venv/bin/python3 docker_app_builder/main.py create --name my-multi-volume-app \
--base-image "ubuntu:22.04" \
--install-commands "apt-get update" "apt-get install -y git" \
--run-command "bash" \
--volume "$HOME/my-code:/code" \
--volume "$HOME/.config/my-app:/app-config" \
--mode terminal \
--run
```

**Arguments for `create`:**
- `--name`: (Required) The name for the container, image, and config file.
- `--base-image`: (Required) The base Docker image.
- `--install-commands`: A list of installation commands (e.g., `"cmd1" "cmd2"`).
- `--run-command`: The command to run in the container.
- `--mode`: The run mode (`terminal`, `background`, or `gui_app`). Defaults to `terminal`.
- `--volume`: (Optional) Mount one or more volumes. Each volume is specified in the format `<host_path>:<container_path>`. Can be specified multiple times (e.g., `--volume /host1:/cont1 --volume /host2:/cont2`). If any volumes are mounted, the **Run Command** will execute from within the *first* mounted volume's directory inside the container by default.
- `--run`: (Flag) Run the container immediately after building.

### Run a Saved Configuration

```bash
./venv/bin/python3 docker_app_builder/main.py run my-dev-env
```

**Arguments for `run`:**
- `name`: (Required) The name of the saved configuration to run.
