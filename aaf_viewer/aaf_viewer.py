from __future__ import (
    unicode_literals,
    absolute_import,
    print_function,
    division,
)
import sys
from PySide2 import QtCore, QtWidgets, QtGui
import aaf2
from qt_aafmodel import AAFModel

class AAFViewer(QtWidgets.QMainWindow):
    def __init__(self):
        super(AAFViewer, self).__init__()
        self.setWindowTitle("AAF Viewer")
        self.current_view_index = 0  # Add current view index tracking


        if sys.platform == 'win32':  # Windows
            # Set application-wide stylesheet for consistent font
            self.setStyleSheet("""
                * {
                    font-family: "Calibri";
                }
            """)
        
        # Create central widget
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QtWidgets.QVBoxLayout(self.central_widget)

        # Define view names
        self.view_names = [
            "All Content",
            "Top Level Objects",
            "Composition Objects",
            "Master Mobs",
            "Source Mobs",
            "Dictionary",
            "MetaDictionary",
            "Root Object"
        ]
        
        # Store view actions for checking
        self.view_actions = {}
        
        
        # For managing tool states
        self.active_tools = set()
        self.tool_widgets = {}
        
        # Create search widget (initially hidden)
        self.createSearchWidget()
        self.search_widget.hide()

        # Add search related member variables
        self.search_results = []  # List to store search results
        self.current_search_index = -1  # Current position in search results
        self.search_text = ""  # Current search text
        self.search_type = "All Fields"  # Current search type
        
        # Create menu bar
        self.createMenuBar()
        
        # Create toolbar
        self.createToolBar()
        
        # Create tree view
        self.createTreeView()
        
        # Get screen width and set window size
        screen = QtWidgets.QApplication.primaryScreen()
        screen_width = screen.size().width()
        screen_height = screen.size().height()
        window_width = int(screen_width * 0.82)
        window_height = int(screen_height * 0.82)
        self.resize(window_width, window_height)
    
    def createMenuBar(self):
        menubar = self.menuBar()

        if sys.platform == 'darwin':  # macOS
            # menubar.setNativeMenuBar(False)
            QtCore.QTimer.singleShot(0, self._createMenuItems)
        else:
            self._createMenuItems()
    
    def _createMenuItems(self):

        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        open_action = QtWidgets.QAction("Open AAF File", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.openFile)
        file_menu.addAction(open_action)
        
        # View menu
        self.view_menu = menubar.addMenu("View")
        view_group = QtWidgets.QActionGroup(self)
        
        # Create an action for each view option
        for i, name in enumerate(self.view_names):
            action = QtWidgets.QAction(name, self)
            action.setCheckable(True)
            action.setActionGroup(view_group)

            # Fix Lambda function definition
            # Use helper function to avoid closure issues
            def make_callback(idx):
                return lambda: self.changeViewByIndex(idx)
            action.triggered.connect(make_callback(i))
            self.view_menu.addAction(action)
            self.view_actions[name] = action
        
        # Select first view by default
        if self.view_actions:
            self.view_actions[self.view_names[0]].setChecked(True)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        # Search tool
        self.search_action = QtWidgets.QAction("Search", self)
        self.search_action.setCheckable(True)
        self.search_action.setShortcut("Ctrl+F")
        self.search_action.triggered.connect(lambda checked: self.toggleTool("search", checked))
        tools_menu.addAction(self.search_action)
        
        # Register search tool to tool management system
        self.tool_widgets["search"] = {
            "widget": self.search_widget,
            "exclusive": False,
            "action": self.search_action
        }
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        about_action = QtWidgets.QAction("About", self)
        about_action.triggered.connect(self.showAbout)
        help_menu.addAction(about_action)
        
    def showAbout(self):
        QtWidgets.QMessageBox.about(
            self,
            "About AAF Viewer",
            "AAF Viewer\n\nA tool for viewing AAF file structure.\n\nCopyright 2025, @xuzhaozheng All rights reserved."
        )
        
    def createToolBar(self):
        toolbar = self.addToolBar("Tools")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonFollowStyle)

        
        # File button with system icon
        file_action = QtWidgets.QAction(QtGui.QIcon.fromTheme("document-open"), "Open AAF File", self)
        file_action.setShortcut("Ctrl+O")
        file_action.triggered.connect(self.openFile)
        toolbar.addAction(file_action)
        
        toolbar.addSeparator()
        
        # Add view selection combo box
        toolbar.addWidget(QtWidgets.QLabel("View "))
        self.view_combo = QtWidgets.QComboBox()
        view_names = self.view_names
        self.view_combo.addItems(view_names)
        self.view_combo.currentIndexChanged.connect(self.changeViewByIndex)
        toolbar.addWidget(self.view_combo)
        
        toolbar.addSeparator()
        
        # Search button with system icon
        self.toolbar_search_action = QtWidgets.QAction(QtGui.QIcon.fromTheme("system-search"), "Search", self)
        self.toolbar_search_action.setCheckable(True)
        self.toolbar_search_action.triggered.connect(lambda checked: self.toggleTool("search", checked))
        toolbar.addAction(self.toolbar_search_action)
    
    def createSearchWidget(self):
        """Create search widget and its components"""
        self.search_widget = QtWidgets.QWidget()
        search_layout = QtWidgets.QHBoxLayout(self.search_widget)
        search_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add search type combo box
        self.search_type = QtWidgets.QComboBox()
        self.search_type.addItems([
            "All Fields",
            "Name",
            "Value",
            "Class"
        ])
        self.search_type.currentTextChanged.connect(self._onSearchTypeChanged)
        search_layout.addWidget(self.search_type)
        
        # Search box
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Search...")
        self.search_box.returnPressed.connect(self._onSearchEnterPressed)
        search_layout.addWidget(self.search_box)
        
        # Match counter label
        self.match_counter = QtWidgets.QLabel("0/0")
        self.match_counter.setMinimumWidth(60)
        search_layout.addWidget(self.match_counter)
        
        # Navigation buttons
        self.prev_button = QtWidgets.QPushButton("Previous")
        self.prev_button.clicked.connect(self.findPrevious)
        self.next_button = QtWidgets.QPushButton("Next")
        self.next_button.clicked.connect(self.findNext)
        
        search_layout.addWidget(self.prev_button)
        search_layout.addWidget(self.next_button)
        
        self.layout.addWidget(self.search_widget)

    def createTreeView(self):
        """Create tree view widget"""
        self.tree = QtWidgets.QTreeView()
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.layout.addWidget(self.tree)
    
    def openFile(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open AAF File",
            "",
            "AAF files (*.aaf);;All files (*.*)"
        )
        if file_path:
            self.current_file = file_path
            self.loadAAFFile()
            
    def loadAAFFile(self):
        if not self.current_file:
            return
            
        try:
            f = aaf2.open(self.current_file)
            self.aaf_file = f  # Save file object for later use
            
            # Define view options after aaf_file is initialized
            self.view_options = {
                "All Content": lambda: self.aaf_file.content,
                "Top Level Objects": lambda: list(self.aaf_file.content.toplevel()),
                "Composition Objects": lambda: list(self.aaf_file.content.compositionmobs()),
                "Master Mobs": lambda: list(self.aaf_file.content.mastermobs()),
                "Source Mobs": lambda: list(self.aaf_file.content.sourcemobs()),
                "Dictionary": lambda: self.aaf_file.dictionary,
                "MetaDictionary": lambda: self.aaf_file.metadict,
                "Root Object": lambda: self.aaf_file.root
            }
            
            # Use current_view_index to restore previous view if it exists
            view_index = self.current_view_index if self.current_view_index else 0
            self.changeViewByIndex(view_index)
            self.setWindowTitle(f"AAF Viewer - {self.current_file}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Error opening file:\n{str(e)}",
                QtWidgets.QMessageBox.Ok
            )
            # Reset view on error
            self.current_view_index = 0
            
    def changeViewByIndex(self, index):
        """Switch view based on index"""
        if not hasattr(self, 'aaf_file'):
            return
            
        if 0 <= index < len(self.view_names):
            self.current_view_index = index  # Update current view index
            view_name = self.view_names[index]
            
            # Update menu item selection state
            for action_name, action in self.view_actions.items():
                action.setChecked(action_name == view_name)
                
            # Update dropdown list selection
            if self.view_combo.currentIndex() != index:
                self.view_combo.setCurrentIndex(index)
                
            # Call view switch function
            self._applyViewChange(view_name)
    
    def changeViewByName(self, view_name):
        """Switch view based on name"""
        if not hasattr(self, 'aaf_file') or not hasattr(self, 'view_options') or view_name not in self.view_options:
            return
        
        # Update current view index
        if view_name in self.view_names:
            self.current_view_index = self.view_names.index(view_name)
        
        # Update menu item selection state
        for action_name, action in self.view_actions.items():
            action.setChecked(action_name == view_name)
        
        # Call view switch function
        self._applyViewChange(view_name)
    
    def _applyViewChange(self, view_name):
        """Apply view change"""
        try:
            # Ensure view_options is defined and aaf_file is loaded
            if not hasattr(self, 'view_options') or not hasattr(self, 'aaf_file'):
                return
            
            # Access view function directly through dictionary
            if view_name in self.view_options:
                root = self.view_options[view_name]()
                model = AAFModel(root)
                self.tree.setModel(model)
                self.tree.expandToDepth(0)
                
                # Set column widths proportionally
                total_width = self.tree.viewport().width()
                self.distribute_width(total_width)
                
                
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Error switching view:\n{str(e)}",
                QtWidgets.QMessageBox.Ok
            )

    def toggleTool(self, tool_id, checked):
        """
        General tool toggle manager

        Args:
            tool_id: Unique identifier for the tool
            checked: Whether to enable the tool
        """
        if tool_id not in self.tool_widgets:
            return
            
        tool_info = self.tool_widgets[tool_id]
        widget = tool_info["widget"]
        exclusive = tool_info.get("exclusive", False)
        action = tool_info["action"]
        
        if checked:
            # If exclusive tool, close other exclusive tools first
            if exclusive:
                for other_id, other_info in self.tool_widgets.items():
                    if other_id != tool_id and other_info.get("exclusive", False):
                        self.toggleTool(other_id, False)
            
            # Activate current tool
            self.active_tools.add(tool_id)
            widget.setVisible(True)
            
            # Synchronize all related action states
            action.setChecked(True)
            if tool_id == "search":
                self.toolbar_search_action.setChecked(True)
        else:
            # Close current tool
            self.active_tools.discard(tool_id)
            widget.setVisible(False)

            # Synchronize all related action states
            action.setChecked(False)
            if tool_id == "search":
                self.toolbar_search_action.setChecked(False)

    def distribute_width(self, total_width):
        self.tree.setColumnWidth(0, int(total_width * 0.3))
        self.tree.setColumnWidth(1, int(total_width * 0.5))
        self.tree.setColumnWidth(2, int(total_width * 0.2))

    def resizeEvent(self, event):
        """Recalculate column widths when window size changes"""
        super(AAFViewer, self).resizeEvent(event)
        if hasattr(self, 'tree') and self.tree.model():
            total_width = self.tree.viewport().width()
            self.distribute_width(total_width)

    # Then implement the handler to manage new searches, findNext, or findPrevious:
    def _onSearchEnterPressed(self):
        text = self.search_box.text()
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        is_shift_pressed = bool(modifiers & QtCore.Qt.ShiftModifier)

        if not text:
            return

        if text == self.search_text:
            if is_shift_pressed:
                self.findPrevious()
            else:
                self.findNext()
        else:
            self._onSearchBegin(text)
    def findNext(self):
        """Find next matching item in the tree view"""
        if not self.search_text:
            return
            
        # Get current model
        model = self.tree.model()
        if not model:
            return
            
        # If no results yet, collect them
        if not self.search_results:
            root_index = model.index(0, 0)
            self._collectSearchResults(root_index)
            
            if not self.search_results:
                QtWidgets.QMessageBox.information(self, "Search", "No matches found")
                return
                
            self.current_search_index = 0
        else:
            # Move to next result
            self.current_search_index = (self.current_search_index + 1) % len(self.search_results)
            
        self._selectSearchResult()
        
    def findPrevious(self):
        """Find previous matching item in the tree view"""
        if not self.search_text:
            return
            
        # Get current model
        model = self.tree.model()
        if not model:
            return
            
        # If no results yet, collect them
        if not self.search_results:
            root_index = model.index(0, 0)
            self._collectSearchResults(root_index)
            
            if not self.search_results:
                QtWidgets.QMessageBox.information(self, "Search", "No matches found")
                return
                
            self.current_search_index = len(self.search_results) - 1
        else:
            # Move to previous result
            self.current_search_index = (self.current_search_index - 1) % len(self.search_results)
            
        self._selectSearchResult()
        
    def _collectSearchResults(self, index):
        """Recursively collect all matching items in the tree"""
        model = self.tree.model()
        if not model:
            return
            
        # Check current item
        if self._itemMatchesSearch(index):
            self.search_results.append(index)
            
        # Check children
        row_count = model.rowCount(index)
        for row in range(row_count):
            child_index = model.index(row, 0, index)
            self._collectSearchResults(child_index)
            
    def _itemMatchesSearch(self, index):
        """Check if an item matches the current search criteria"""
        model = self.tree.model()
        if not model:
            return False
            
        # Get item data with Qt.DisplayRole
        name = model.data(model.index(index.row(), 0, index.parent()), QtCore.Qt.DisplayRole)
        value = model.data(model.index(index.row(), 1, index.parent()), QtCore.Qt.DisplayRole)
        class_name = model.data(model.index(index.row(), 2, index.parent()), QtCore.Qt.DisplayRole)
        
        # Convert to string for comparison
        name = str(name) if name else ""
        value = str(value) if value else ""
        class_name = str(class_name) if class_name else ""
        
        # Perform search based on type
        if self.search_type == "All Fields":
            return (self.search_text.lower() in name.lower() or 
                   self.search_text.lower() in value.lower() or 
                   self.search_text.lower() in class_name.lower())
        elif self.search_type == "Name":
            return self.search_text.lower() in name.lower()
        elif self.search_type == "Value":
            return self.search_text.lower() in value.lower()
        elif self.search_type == "Class":
            return self.search_text.lower() in class_name.lower()
            
        return False
        
    def _selectSearchResult(self):
        """Select and scroll to the current search result"""
        if not self.search_results or self.current_search_index < 0:
            return
            
        # Get the current result index
        index = self.search_results[self.current_search_index]
        
        # Select and scroll to the item
        self.tree.setCurrentIndex(index)
        self.tree.scrollTo(index)
        
        # Update match counter
        self.updateMatchCounter()
        
    def updateMatchCounter(self):
        """Update the match counter label with current position and total matches"""
        if not self.search_results:
            self.match_counter.setText("0/0")
            return
            
        total = len(self.search_results)
        current = self.current_search_index + 1 if self.current_search_index >= 0 else 0
        self.match_counter.setText(f"{current}/{total}")

    def _onSearchBegin(self, text):
        """Handle search text changes"""
        self.search_text = text
        self.current_search_index = -1
        self.search_results = []
        self.match_counter.setText("0/0")
        
        if text:
            # Get current model
            model = self.tree.model()
            if model:
                # Get all items in the tree
                root_index = model.index(0, 0)
                self._collectSearchResults(root_index)
                
                if self.search_results:
                    self.current_search_index = 0
                    self._selectSearchResult()

    def _onSearchTypeChanged(self, search_type):
        """Handle search type changes"""
        self.search_type = search_type
        self.current_search_index = -1
        self.search_results = []
        self.match_counter.setText("0/0")
        
        if self.search_text:
            # Get current model
            model = self.tree.model()
            if model:
                # Get all items in the tree
                root_index = model.index(0, 0)
                self._collectSearchResults(root_index)
                
                if self.search_results:
                    self.current_search_index = 0
                    self._selectSearchResult()

if __name__ == "__main__":

    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)

    app = QtWidgets.QApplication(sys.argv)
    
    try:
        viewer = AAFViewer()
        viewer.show()

        # Process CLI arguments and automatically open a file path if one is provided
        if len(sys.argv) > 1 and sys.argv[1].endswith('.aaf'):
            viewer.current_file = sys.argv[1]
            viewer.loadAAFFile()
            
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Error starting application: {str(e)}")