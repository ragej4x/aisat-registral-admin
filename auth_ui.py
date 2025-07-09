import sys
import os
import requests
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QLineEdit, QMessageBox, QFormLayout, QCheckBox)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont

API_BASE_URL = "https://jimboyaczon.pythonanywhere.com"

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('AISAT Admin Login')
        self.setGeometry(0, 0, 400, 300)
        self.setFixedSize(400, 300)
        
        self.settings = QSettings("AISAT", "AdminPanel")
        self.registration_open = False
        self.admin_name = "Admin" # To store the name on successful login
        
        layout = QVBoxLayout()
        
        title_label = QLabel("AISAT Admin Login")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50; margin-bottom: 20px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        form_layout = QFormLayout()
        
        self.idno_input = QLineEdit()
        self.idno_input.setPlaceholderText("Enter your ID Number")
        form_layout.addRow("ID Number:", self.idno_input)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter your password")
        form_layout.addRow("Password:", self.password_input)
        
        self.remember_checkbox = QCheckBox("Remember me")
        form_layout.addRow("", self.remember_checkbox)
        
        layout.addLayout(form_layout)
        
        self.login_button = QPushButton("Login")
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #2980b9;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
            QPushButton:pressed {
                background-color: #1c6ea4;
            }
        """)
        self.login_button.clicked.connect(self.attempt_login)
        layout.addWidget(self.login_button)
        
        register_layout = QHBoxLayout()
        register_label = QLabel("Don't have an account?")
        self.register_link = QPushButton("Register")
        self.register_link.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #2980b9;
                border: none;
                text-decoration: underline;
            }
            QPushButton:hover {
                color: #3498db;
            }
        """)
        self.register_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.register_link.clicked.connect(self.open_registration)
        register_layout.addWidget(register_label)
        register_layout.addWidget(self.register_link)
        register_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(register_layout)
        
        self.setLayout(layout)
        self.load_credentials()
    
    def load_credentials(self):
        if self.settings.value("remember_me", False, type=bool):
            self.idno_input.setText(self.settings.value("idno", ""))
            self.password_input.setText(self.settings.value("password", ""))
            self.remember_checkbox.setChecked(True)
    
    def save_credentials(self):
        if self.remember_checkbox.isChecked():
            self.settings.setValue("remember_me", True)
            self.settings.setValue("idno", self.idno_input.text())
            self.settings.setValue("password", self.password_input.text())
        else:
            self.settings.setValue("remember_me", False)
            self.settings.remove("idno")
            self.settings.remove("password")
    
    def attempt_login(self):
        idno = self.idno_input.text()
        password = self.password_input.text()
        
        if not idno or not password:
            QMessageBox.warning(self, "Login Error", "Please enter both ID number and password.")
            return
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/auth/login",
                json={"idno": idno, "password": password},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("token")
                
                if not data.get("is_admin"):
                    QMessageBox.warning(self, "Access Denied", "You do not have admin privileges.")
                    return
                
                self.save_credentials()
                self.settings.setValue("auth_token", token)
                self.admin_name = data.get('name', 'Admin') # Store the name
                self.settings.setValue("admin_name", self.admin_name) # Save admin name in settings
                QMessageBox.information(self, "Login Successful", f"Welcome, {self.admin_name}!")
                self.accept()
            else:
                error_msg = response.json().get("error", "Invalid credentials")
                QMessageBox.warning(self, "Login Failed", error_msg)
        
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Connection Error", f"Could not connect to server: {str(e)}")
    
    def open_registration(self):
        self.registration_open = True
        self.hide()
        reg_dialog = RegistrationDialog(self)
        result = reg_dialog.exec_()
        self.registration_open = False
        self.show()
    
    def get_admin_name(self):
        """Returns the name of the logged-in admin."""
        return self.admin_name

    def reject(self):
        if not self.registration_open:
            super().reject()


class RegistrationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('AISAT Admin Registration')
        self.setGeometry(0, 0, 500, 400)
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout()
        
        title_label = QLabel("AISAT Admin Registration")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50; margin-bottom: 20px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        form_layout = QFormLayout()
        
        self.fullname_input = QLineEdit()
        self.fullname_input.setPlaceholderText("Enter your full name")
        form_layout.addRow("Full Name:", self.fullname_input)
        
        self.idno_input = QLineEdit()
        self.idno_input.setPlaceholderText("Enter your ID Number")
        form_layout.addRow("ID Number:", self.idno_input)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email address")
        form_layout.addRow("Email:", self.email_input)
        
        self.contact_input = QLineEdit()
        self.contact_input.setPlaceholderText("Enter your contact number")
        form_layout.addRow("Contact Number:", self.contact_input)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter your password")
        form_layout.addRow("Password:", self.password_input)
        
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input.setPlaceholderText("Confirm your password")
        form_layout.addRow("Confirm Password:", self.confirm_password_input)
        
        layout.addLayout(form_layout)
        
        self.register_button = QPushButton("Register")
        self.register_button.setStyleSheet("""
            QPushButton {
                background-color: #2980b9;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
            QPushButton:pressed {
                background-color: #1c6ea4;
            }
        """)
        self.register_button.clicked.connect(self.attempt_registration)
        layout.addWidget(self.register_button)
        
        back_layout = QHBoxLayout()
        back_label = QLabel("Already have an account?")
        self.back_link = QPushButton("Back to Login")
        self.back_link.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #2980b9;
                border: none;
                text-decoration: underline;
            }
            QPushButton:hover {
                color: #3498db;
            }
        """)
        self.back_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_link.clicked.connect(self.back_to_login)
        back_layout.addWidget(back_label)
        back_layout.addWidget(self.back_link)
        back_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(back_layout)
        
        self.setLayout(layout)
    
    def attempt_registration(self):
        fullname = self.fullname_input.text()
        idno = self.idno_input.text()
        email = self.email_input.text()
        contact = self.contact_input.text()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        
        if not all([fullname, idno, email, contact, password, confirm_password]):
            QMessageBox.warning(self, "Registration Error", "Please fill in all required fields.")
            return
        
        if password != confirm_password:
            QMessageBox.warning(self, "Registration Error", "Passwords do not match.")
            return
        
        registration_data = {
            "full_name": fullname,
            "id_no": idno,
            "email": email,
            "contact_no": contact,
            "password": password
        }
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/auth/register",
                json=registration_data,
                timeout=5
            )
            
            if response.status_code == 201:
                QMessageBox.information(self, "Registration Successful", "Your admin account has been created. You may now login.")
                self.accept()
            else:
                error_msg = response.json().get("error", "Registration failed")
                QMessageBox.warning(self, "Registration Failed", error_msg)
        
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Connection Error", f"Could not connect to server: {str(e)}")
    
    def back_to_login(self):
        self.reject()


def check_session(settings):
    token = settings.value("auth_token", "")
    
    if not token:
        return False, None
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/auth/verify",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("valid") and data.get("is_admin"):
                return True, data.get("name", "Admin")
        
        settings.remove("auth_token")
        return False, None
    
    except requests.exceptions.RequestException:
        # If the server is unreachable, use cached admin name if available
        cached_name = settings.value("admin_name", "Admin")
        return True, cached_name  # Trust the token when server is unreachable 