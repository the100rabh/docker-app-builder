import sys
import re
import argparse
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QFileDialog, QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QFormLayout
from PyQt6.QtCore import QThread, pyqtSignal, QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator

# GUI is optional, so handle import error
try:
    from ui import Ui_MainWindow
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

import config_manager
import docker_handler

# --- GUI Application ---

if GUI_AVAILABLE:
    # Regex for valid Docker container names
    CONTAINER_NAME_REGEX = QRegularExpression("^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")

    class Worker(QThread):
        """Worker thread for long-running Docker operations."""
        log = pyqtSignal(str)
        finished = pyqtSignal(object)

        def __init__(self, fn, *args, **kwargs):
            super().__init__()
            self.fn = fn
            self.args = args
            self.kwargs = kwargs

        def run(self):
            try:
                # The worker needs to pass the log_callback to the function
                kwargs = self.kwargs.copy()
                kwargs['log_callback'] = self.log.emit
                result = self.fn(*self.args, **kwargs)
                self.finished.emit(result)
            except Exception as e:
                self.log.emit(f"--- THREAD ERROR ---")
                self.log.emit(str(e))
                self.finished.emit(None)

    class AddVolumeDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Add Volume Mount")
            self.layout = QVBoxLayout(self)

            self.formLayout = QFormLayout()
            self.hostPathInput = QLineEdit()
            self.hostPathButton = QPushButton("Browse...")
            self.hostPathButton.clicked.connect(self.browse_host_path)
            self.hostPathLayout = QHBoxLayout()
            self.hostPathLayout.addWidget(self.hostPathInput)
            self.hostPathLayout.addWidget(self.hostPathButton)
            self.formLayout.addRow("Host Path:", self.hostPathLayout)

            self.containerPathInput = QLineEdit("/data")
            self.formLayout.addRow("Container Path:", self.containerPathInput)
            self.layout.addLayout(self.formLayout)

            self.buttonLayout = QHBoxLayout()
            self.okButton = QPushButton("OK")
            self.okButton.clicked.connect(self.accept)
            self.cancelButton = QPushButton("Cancel")
            self.cancelButton.clicked.connect(self.reject)
            self.buttonLayout.addWidget(self.okButton)
            self.buttonLayout.addWidget(self.cancelButton)
            self.layout.addLayout(self.buttonLayout)

        def browse_host_path(self):
            path = QFileDialog.getExistingDirectory(self, "Select Host Path")
            if path:
                self.hostPathInput.setText(path)
        
        def get_volume_paths(self):
            return self.hostPathInput.text(), self.containerPathInput.text()

    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.ui = Ui_MainWindow()
            self.ui.setupUi(self)
            self.setWindowTitle("Docker App Builder")
            self.worker = None

            self.ui.logPane.setReadOnly(True)
            validator = QRegularExpressionValidator(CONTAINER_NAME_REGEX, self)
            self.ui.containerNameInput.setValidator(validator)

            # Connect UI Signals
            self.ui.createButton.clicked.connect(lambda: self.create_container(run_after=True))
            self.ui.rebuildButton.clicked.connect(lambda: self.create_container(run_after=True, nocache=True))
            self.ui.runButton.clicked.connect(self.run_container_from_ui)
            self.ui.loadButton.clicked.connect(self.load_selected_config)
            self.ui.configListWidget.currentItemChanged.connect(self.load_selected_config)
            self.ui.addVolumeButton.clicked.connect(self.add_volume_entry)
            self.ui.removeVolumeButton.clicked.connect(self.remove_volume_entry)
            
            self.refresh_config_list()
            self.set_ui_loading(False)

        def log(self, message):
            self.ui.logPane.append(message)
            self.ui.logPane.verticalScrollBar().setValue(self.ui.logPane.verticalScrollBar().maximum())

        def set_ui_loading(self, is_loading):
            self.ui.createButton.setDisabled(is_loading)
            self.ui.rebuildButton.setDisabled(is_loading)
            self.ui.runButton.setDisabled(is_loading)

        def refresh_config_list(self):
            self.ui.configListWidget.clear()
            configs = config_manager.get_saved_configs()
            self.ui.configListWidget.addItems(configs)

        def add_volume_entry(self):
            dialog = AddVolumeDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                host_path, container_path = dialog.get_volume_paths()
                if host_path and container_path:
                    self.ui.volumeListWidget.addItem(f"{host_path}:{container_path}")
        
        def remove_volume_entry(self):
            for item in self.ui.volumeListWidget.selectedItems():
                self.ui.volumeListWidget.takeItem(self.ui.volumeListWidget.row(item))

        def load_selected_config(self):
            selected_item = self.ui.configListWidget.currentItem()
            if not selected_item:
                return
            
            config_name = selected_item.text()
            config = config_manager.load_config(config_name)
            if config:
                self.ui.containerNameInput.setText(config.get("container_name", ""))
                self.ui.baseImageCombo.setCurrentText(config.get("base_image", ""))
                self.ui.installCommandsInput.setText("\n".join(config.get("install_commands", [])))
                self.ui.runCommandInput.setText(config.get("run_command", ""))
                
                # Volumes
                self.ui.volumeListWidget.clear()
                for vol_map in config.get("volumes", []):
                    self.ui.volumeListWidget.addItem(f"{vol_map['host']}:{vol_map['container']}")

                # Mode
                mode = config.get("mode", "terminal")
                if mode == "terminal": self.ui.terminalRadio.setChecked(True)
                elif mode == "background": self.ui.backgroundRadio.setChecked(True)
                elif mode == "gui_app": self.ui.guiAppRadio.setChecked(True)

                # Host Access
                self.ui.hostAccessCheckbox.setChecked(config.get("host_access", False))

                # Network Mode
                net_mode = config.get("network_mode", "bridge")
                if net_mode == "host": self.ui.hostNetworkRadio.setChecked(True)
                else: self.ui.bridgeRadio.setChecked(True)
                
                self.log(f"Loaded configuration '{config_name}'.")

        def gather_ui_data(self):
            if not self.ui.containerNameInput.hasAcceptableInput():
                QMessageBox.warning(self, "Invalid Name", "Please enter a valid container name.")
                return None
            
            volumes = []
            for i in range(self.ui.volumeListWidget.count()):
                item = self.ui.volumeListWidget.item(i)
                host_path, container_path = item.text().split(':', 1)
                volumes.append({'host': host_path, 'container': container_path})

            data = {
                "container_name": self.ui.containerNameInput.text(),
                "base_image": self.ui.baseImageCombo.currentText(),
                "install_commands": self.ui.installCommandsInput.toPlainText().splitlines(),
                "run_command": self.ui.runCommandInput.text(),
                "mode": ("terminal" if self.ui.terminalRadio.isChecked() else
                         "background" if self.ui.backgroundRadio.isChecked() else "gui_app"),
                "volumes": volumes,
                "host_access": self.ui.hostAccessCheckbox.isChecked(),
                "network_mode": "host" if self.ui.hostNetworkRadio.isChecked() else "bridge",
            }
            return data

        def create_container(self, run_after=False, nocache=False):
            config_data = self.gather_ui_data()
            if not config_data: return

            self.set_ui_loading(True)
            self.log("Starting build process...")
            
            self.worker = Worker(docker_handler.build_image, 
                                 tag=config_data["container_name"],
                                 base_image=config_data["base_image"],
                                 install_commands=config_data["install_commands"],
                                 nocache=nocache)
            self.worker.log.connect(self.log)
            self.worker.finished.connect(lambda image: self.on_build_finished(image, config_data, run_after))
            self.worker.start()

        def on_build_finished(self, image, config_data, run_after=False):
            if image:
                self.log(f"Build successful. Image ID: {image.short_id}")
                config_data["image_id"] = image.id
                config_manager.save_config(config_data)
                self.refresh_config_list()
                if run_after:
                    self.run_container_from_ui()
                else:
                    self.set_ui_loading(False)
            else:
                self.log("Build failed. See logs for details.")
                QMessageBox.critical(self, "Build Failed", "The Docker image could not be built.")
                self.set_ui_loading(False)

        def run_container_from_ui(self):
            config_data = self.gather_ui_data()
            if not config_data: return

            self.set_ui_loading(True)
            self.log(f"Attempting to run '{config_data['container_name']}'...")
            
            self.worker = Worker(docker_handler.run_container,
                                 image_tag=config_data["container_name"],
                                 container_name=config_data["container_name"],
                                 run_command=config_data["run_command"],
                                 mode=config_data["mode"],
                                 volumes=config_data["volumes"],
                                 host_access=config_data.get("host_access", False),
                                 network_mode=config_data.get("network_mode", "bridge")) # Pass network_mode
            self.worker.log.connect(self.log)
            self.worker.finished.connect(self.on_run_finished)
            self.worker.start()

        def on_run_finished(self, result):
            self.set_ui_loading(False)
            if result:
                self.log("Run command sent successfully.")
            else:
                self.log("Run command failed. Check logs.")

# --- CLI Handlers ---

def handle_create(args):
    """CLI handler for the 'create' command."""
    print("Starting build process...")
    
    volumes = []
    if args.volume:
        for vol_str in args.volume:
            if ":" not in vol_str:
                print(f"Error: --volume argument '{vol_str}' must be in the format <host_path>:<container_path>")
                sys.exit(1)
            host_path, container_path = vol_str.split(":", 1)
            volumes.append({'host': host_path, 'container': container_path})

    config_data = {
        "container_name": args.name,
        "base_image": args.base_image,
        "install_commands": args.install_commands,
        "run_command": args.run_command,
        "mode": args.mode,
        "volumes": volumes,
        "host_access": args.host_access,
        "network_mode": args.network_mode,
    }
    
    image = docker_handler.build_image(
        tag=config_data["container_name"],
        base_image=config_data["base_image"],
        install_commands=config_data["install_commands"],
        nocache=args.no_cache
    )
    
    if image:
        print(f"Build successful. Image ID: {image.short_id}")
        config_data["image_id"] = image.id
        config_manager.save_config(config_data)
        print(f"Configuration '{args.name}' saved.")
        if args.run:
            handle_run(args)
    else:
        print("Build failed.")
        sys.exit(1)

def handle_run(args):
    """CLI handler for the 'run' command."""
    print(f"Attempting to run '{args.name}'...")
    config = config_manager.load_config(args.name)
    if not config:
        print(f"Error: Configuration '{args.name}' not found.")
        sys.exit(1)
        
    docker_handler.run_container(
        image_tag=config["container_name"],
        container_name=config["container_name"],
        run_command=config.get("run_command", ""),
        mode=config.get("mode", "terminal"),
        volumes=config.get("volumes", []),
        host_access=config.get("host_access", False),
        network_mode=config.get("network_mode", "bridge")
    )

# --- Main Execution ---

def main():
    parser = argparse.ArgumentParser(description="Docker App Builder")
    subparsers = parser.add_subparsers(dest='command')

    # Create command
    create_parser = subparsers.add_parser('create', help='Build a new container image and configuration.')
    create_parser.add_argument("--name", required=True, help="Container name (used for image tag and config file).")
    create_parser.add_argument("--base-image", required=True, help="Base Docker image (e.g., 'ubuntu:22.04').")
    create_parser.add_argument("--install-commands", nargs='+', default=[], help="List of shell commands for installation.")
    create_parser.add_argument("--run-command", default="", help="The command to execute when the container starts.")
    create_parser.add_argument("--mode", choices=['terminal', 'background', 'gui_app'], default='terminal', help="Run mode.")
    create_parser.add_argument("--volume", nargs='*', help="Mount volumes in the format <host_path>:<container_path> (can be specified multiple times).")
    create_parser.add_argument("--run", action='store_true', help="Run the container immediately after a successful build.")
    create_parser.add_argument("--no-cache", action='store_true', help="Do not use cache when building the image.")
    create_parser.add_argument("--host-access", action='store_true', help="Enable access to host services via host.docker.internal.")
    create_parser.add_argument("--network-mode", choices=['bridge', 'host'], default='bridge', help="Network mode (bridge or host).")
    create_parser.set_defaults(func=handle_create)

    # Run command
    run_parser = subparsers.add_parser('run', help='Run a container from a saved configuration.')
    run_parser.add_argument("name", help="Name of the configuration to run.")
    run_parser.set_defaults(func=handle_run)

    # If CLI args are provided, handle them. Otherwise, launch GUI.
    if len(sys.argv) > 1:
        args = parser.parse_args()
        if args.command:
            config_manager.get_config_dir()
            args.func(args)
        else:
            parser.print_help()
    else:
        if GUI_AVAILABLE:
            config_manager.get_config_dir()
            app = QApplication(sys.argv)
            window = MainWindow()
            window.show()
            sys.exit(app.exec())
        else:
            print("GUI is not available. Please use the command-line interface.")
            parser.print_help()


if __name__ == "__main__":
    main()
