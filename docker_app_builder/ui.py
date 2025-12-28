
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QTextEdit, QRadioButton,
    QPushButton, QListWidget, QLabel, QGroupBox
)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 600)
        self.centralWidget = QWidget(MainWindow)
        MainWindow.setCentralWidget(self.centralWidget)

        # Main layout
        self.mainLayout = QHBoxLayout(self.centralWidget)

        # Left side (inputs)
        self.leftWidget = QWidget()
        self.leftLayout = QVBoxLayout(self.leftWidget)
        self.mainLayout.addWidget(self.leftWidget, 1) # Give more space to inputs

        # Right side (configs and logs)
        self.rightWidget = QWidget()
        self.rightLayout = QVBoxLayout(self.rightWidget)
        self.mainLayout.addWidget(self.rightWidget, 1)

        # --- Left Side Components ---

        # Form layout for inputs
        self.formLayout = QFormLayout()

        self.containerNameInput = QLineEdit()
        self.formLayout.addRow("Container Name:", self.containerNameInput)

        self.baseImageCombo = QComboBox()
        self.baseImageCombo.addItems(["ubuntu:22.04", "alpine:3.18", "python:3.11"])
        self.baseImageCombo.setEditable(True)
        self.formLayout.addRow("Base Image:", self.baseImageCombo)

        self.leftLayout.addLayout(self.formLayout)

        self.installCommandsLabel = QLabel("Installation Commands:")
        self.installCommandsInput = QTextEdit()
        self.installCommandsInput.setPlaceholderText("apt-get update && apt-get install -y your-package\npip install -r requirements.txt")
        self.leftLayout.addWidget(self.installCommandsLabel)
        self.leftLayout.addWidget(self.installCommandsInput)

        self.runCommandInput = QLineEdit()
        self.leftLayout.addWidget(QLabel("Run Command:"))
        self.leftLayout.addWidget(self.runCommandInput)

        # Volume Mounts
        self.volumeBox = QGroupBox("Volume Mounts (Optional)")
        self.volumeMainLayout = QVBoxLayout()
        self.volumeListWidget = QListWidget()
        self.volumeMainLayout.addWidget(self.volumeListWidget)
        self.volumeButtonLayout = QHBoxLayout()
        self.addVolumeButton = QPushButton("Add")
        self.removeVolumeButton = QPushButton("Remove")
        self.volumeButtonLayout.addWidget(self.addVolumeButton)
        self.volumeButtonLayout.addWidget(self.removeVolumeButton)
        self.volumeMainLayout.addLayout(self.volumeButtonLayout)
        self.volumeBox.setLayout(self.volumeMainLayout)
        self.leftLayout.addWidget(self.volumeBox)

        # Run mode radio buttons
        self.modeBox = QGroupBox("Run Mode")
        self.modeLayout = QHBoxLayout()
        self.terminalRadio = QRadioButton("Terminal (-it)")
        self.backgroundRadio = QRadioButton("Background (-d)")
        self.guiAppRadio = QRadioButton("GUI App (X11)")
        self.terminalRadio.setChecked(True)
        self.modeLayout.addWidget(self.terminalRadio)
        self.modeLayout.addWidget(self.backgroundRadio)
        self.modeLayout.addWidget(self.guiAppRadio)
        self.modeBox.setLayout(self.modeLayout)
        self.leftLayout.addWidget(self.modeBox)
        
        # Action buttons
        self.buttonLayout = QHBoxLayout()
        self.createButton = QPushButton("Create & Run")
        self.runButton = QPushButton("Run")
        self.loadButton = QPushButton("Load Config")
        self.buttonLayout.addWidget(self.createButton)
        self.buttonLayout.addWidget(self.runButton)
        self.buttonLayout.addWidget(self.loadButton)
        self.leftLayout.addLayout(self.buttonLayout)

        # --- Right Side Components ---

        self.configListLabel = QLabel("Saved Configurations:")
        self.configListWidget = QListWidget()
        self.rightLayout.addWidget(self.configListLabel)
        self.rightLayout.addWidget(self.configListWidget)

        self.logLabel = QLabel("Log Output:")
        self.logPane = QTextEdit()
        self.logPane.setReadOnly(True)
        self.rightLayout.addWidget(self.logLabel)
        self.rightLayout.addWidget(self.logPane)
