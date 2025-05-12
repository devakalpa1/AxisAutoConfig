#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AxisAutoConfig
GUI Tour implementation
"""

import sys
import os
from PySide6.QtWidgets import (QWidget, QLabel, QPushButton, QCheckBox, 
                              QVBoxLayout, QHBoxLayout, QApplication)
from PySide6.QtCore import Qt, QSettings, QPropertyAnimation, QRect, QObject, QPoint, QTimer
from PySide6.QtGui import QPainter, QPen, QColor, QBrush


class TourOverlay(QWidget):
    """
    Transparent overlay widget that highlights specific parts of the UI
    and displays tour instructions
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Make this a transparent overlay that covers the entire parent
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # Initialize variables
        self.highlight_rect = None
        self.is_active = False
        
    def set_highlight_rect(self, rect):
        """Set the rectangle to highlight"""
        self.highlight_rect = rect
        self.update()
        
    def paintEvent(self, event):
        """Custom paint event to create highlight effect"""
        if not self.is_active or not self.highlight_rect:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create semi-transparent dark overlay for entire window with low opacity
        painter.fillRect(self.rect(), QColor(0, 0, 0, 80))  # Reduced opacity from 128 to 80
        
        # Create a less-transparent highlight area rather than completely clear it
        highlight_color = QColor(255, 255, 255, 40)  # Very light highlight with some transparency
        painter.setPen(Qt.NoPen)
        painter.setBrush(highlight_color)
        painter.drawRect(self.highlight_rect)
        
        # Draw a border around the highlighted area
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        pen = QPen(QColor(0, 120, 215), 2, Qt.SolidLine)
        painter.setPen(pen)
        painter.drawRect(self.highlight_rect)


class TourPopup(QWidget):
    """Pop-up widget showing tour step information"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configure window appearance - make it a child window of the main window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        # Remove translucent background to make it more visible
        self.setAttribute(Qt.WA_NoSystemBackground, False)
        
        # Create layout
        self.layout = QVBoxLayout(self)
        
        # Title and content
        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
        
        self.content_label = QLabel()
        self.content_label.setStyleSheet("color: white;")
        self.content_label.setWordWrap(True)
        
        # Bottom row with checkbox and buttons
        bottom_layout = QHBoxLayout()
        
        self.dont_show_checkbox = QCheckBox("Don't show again")
        self.dont_show_checkbox.setStyleSheet("color: white;")
        
        self.next_button = QPushButton("Next")
        self.stop_button = QPushButton("Skip Tour")
        
        bottom_layout.addWidget(self.dont_show_checkbox)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.stop_button)
        bottom_layout.addWidget(self.next_button)
        
        # Add all widgets to main layout
        self.layout.addWidget(self.title_label)
        self.layout.addWidget(self.content_label)
        self.layout.addLayout(bottom_layout)
        
        # Style the widget with solid background
        self.setStyleSheet("""
            TourPopup {
                background-color: rgb(0, 120, 215);
                border-radius: 8px;
                padding: 0px;
            }
            QPushButton {
                background-color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                color: #000000;
                font-weight: bold;
            }
            QLabel {
                margin: 5px;
            }
        """)
        
        self.setMinimumWidth(300)
        self.setMaximumWidth(400)


class GUITour(QObject):
    """
    GUI Tour controller that manages the tour through the application
    """
    
    def __init__(self, main_window):
        """
        Initialize the GUI Tour
        
        Args:
            main_window: The main application window
        """
        super().__init__()
        self.main_window = main_window
        
        # Create overlay and popup with main window as parent
        self.overlay = TourOverlay(self.main_window)
        self.popup = TourPopup(self.main_window)
        
        # Initialize tour state
        self.current_step = 0
        self.is_touring = False
        
        # Define tour steps
        self.tour_steps = [
            {
                "title": "Network Setup",
                "content": "This section allows you to configure the DHCP server to assign temporary IPs to your cameras during setup.",
                "widget": "network_setup_section"
            },
            {
                "title": "Camera Discovery",
                "content": "Once the DHCP server is running, discover cameras and configure their parameters here.",
                "widget": "config_inputs_section"
            },
            {
                "title": "CSV Options",
                "content": "Load your CSV file with IP assignments here. Remember to select the right mode (Sequential or MAC-specific).",
                "widget": "config_inputs_section"
            },
            {
                "title": "Real-time Log",
                "content": "This section displays the progress and results of the configuration process.",
                "widget": "log_section"
            },
            {
                "title": "Completion Report",
                "content": "After configuration, you can save an inventory report from this section.",
                "widget": "completion_section"
            }
        ]
        
        # Connect signals
        self.popup.next_button.clicked.connect(self.next_step)
        self.popup.stop_button.clicked.connect(self.stop_tour)
        
    def start_tour(self):
        """Start the GUI tour from the beginning"""
        # Check if we need to resize the main window first
        if self.main_window.width() < 800 or self.main_window.height() < 600:
            self.main_window.resize(900, 700)
            
        # Prepare the overlay
        self.overlay.resize(self.main_window.size())
        self.overlay.is_active = True
        self.overlay.show()
        
        # Reset to first step
        self.current_step = 0
        self.is_touring = True
        
        # Show the first step
        self._show_current_step()
        
    def next_step(self):
        """Advance to the next step of the tour"""
        self.current_step += 1
        
        if self.current_step >= len(self.tour_steps):
            self.stop_tour()
            return
            
        self._show_current_step()
        
    def stop_tour(self):
        """Stop the tour"""
        self.is_touring = False
        
        # Hide the UI elements
        if self.overlay:
            self.overlay.is_active = False
            self.overlay.hide()
            
        if self.popup:
            self.popup.hide()
            
        # Save preference if "don't show again" is checked
        if self.popup.dont_show_checkbox.isChecked():
            settings = QSettings("AxisAutoConfig", "SetupTool")
            settings.setValue("ShowGUITour", False)
    
    def _show_current_step(self):
        """Show the current tour step"""
        if not self.is_touring or self.current_step >= len(self.tour_steps):
            return
            
        step = self.tour_steps[self.current_step]
        
        # Get the target widget
        target_widget = getattr(self.main_window, step["widget"], None)
        if not target_widget:
            self.next_step()  # Skip this step if widget not found
            return
            
        # Set the highlight area
        target_rect = QRect(target_widget.mapTo(self.main_window, target_widget.rect().topLeft()), 
                            target_widget.size())
        self.overlay.set_highlight_rect(target_rect)
        
        # Update popup content
        self.popup.title_label.setText(step["title"])
        self.popup.content_label.setText(step["content"])
        
        # Update next button text on last step
        if self.current_step == len(self.tour_steps) - 1:
            self.popup.next_button.setText("Finish")
        else:
            self.popup.next_button.setText("Next")
        
        # Position and show the popup
        popup_x = target_rect.right() + 10
        popup_y = target_rect.center().y() - self.popup.height() // 2
        
        # Make sure popup is fully visible
        if popup_x + self.popup.width() > self.main_window.width():
            popup_x = target_rect.left() - 10 - self.popup.width()
            
        if popup_x < 0:
            popup_x = self.main_window.width() // 2 - self.popup.width() // 2
            popup_y = target_rect.bottom() + 10
            
        if popup_y < 0:
            popup_y = 10
        elif popup_y + self.popup.height() > self.main_window.height():
            popup_y = self.main_window.height() - self.popup.height() - 10
        
        self.popup.move(self.main_window.mapToGlobal(QPoint(popup_x, popup_y)))
        self.popup.show()
