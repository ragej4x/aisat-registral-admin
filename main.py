import sys
import os
import requests
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QFrame, QSizePolicy,
                            QMessageBox, QStackedWidget, QDialog, QLineEdit, 
                            QFormLayout, QDialogButtonBox, QCheckBox, QSlider)
from PyQt5.QtCore import Qt, QSettings, QUrl
from PyQt5.QtGui import QFont, QIcon, QPixmap
from datetime import datetime, timedelta

# QWebEngineView is required for this functionality.
# If you don't have it, please install it: pip install PyQtWebEngine
from PyQt5.QtWebEngineWidgets import QWebEngineView

# Import authentication UI components
from auth_ui import LoginDialog, check_session

# API base URL - this should match the server.py port
API_BASE_URL = "https://jimboyaczon.pythonanywhere.com"

# Theme colors - matching the HTML files in sideload directory
THEME_COLORS = {
    "light": {
        "bg_primary": "#f8f9fa",
        "bg_secondary": "#ffffff",
        "text_primary": "#2d2a2e",
        "text_secondary": "#5a5a5a",
        "accent_color": "#3498db",
        "accent_hover": "#2980b9",
        "border_color": "#e9ecef",
        "shadow_color": "rgba(0,0,0,0.05)",
        "sidebar_bg": "#2c3e50",
        "sidebar_text": "#ffffff",  # White text for sidebar
        "sidebar_hover": "#34495e",
        "sidebar_active": "#2980b9"
    },
    "dark": {
        "bg_primary": "#2d2a2e",
        "bg_secondary": "#3b3842",
        "text_primary": "#fcfcfa",
        "text_secondary": "#c1c0c0",
        "accent_color": "#78dce8",
        "accent_hover": "#5fb9c5",
        "border_color": "#4a474e",
        "shadow_color": "rgba(0,0,0,0.2)",
        "sidebar_bg": "#1e1e1e",
        "sidebar_text": "#fcfcfa",  # Light text for sidebar
        "sidebar_hover": "#2d2d2d",
        "sidebar_active": "#5fb9c5"
    }
}

class WebEngineView(QWebEngineView):
    """A custom web view to handle token injection for authenticated sessions."""
    def __init__(self, token, initial_js_call=None, theme=None):
        super(WebEngineView, self).__init__()
        self.token = token
        self.initial_js_call = initial_js_call
        self.theme = theme
        # When the page finishes loading, inject the token and API base URL
        self.loadFinished.connect(self._on_load_finished)
        
        # Set up URL handler for PDF export
        self.page().profile().downloadRequested.connect(self.handle_download)
        self.urlChanged.connect(self.handle_url_changed)
    
    def handle_url_changed(self, url):
        """Handle custom URL schemes"""
        url_string = url.toString()
        if url_string.startswith("pyqt://export_pdf"):
            # This will be handled by the form submission
            print("PDF export URL detected")
    
    def handle_download(self, download):
        """Handle file downloads"""
        print(f"Download requested: {download.url().toString()}")
        download.accept()
    
    def createWindow(self, type_):
        """Create a new window for form submissions"""
        # For different PyQt versions, the tab type might be different
        # Let's check if it's a new window/tab request and handle it
        if type_ == 1:  # 1 is typically WebBrowserTab in most PyQt versions
            # Create a temporary view to handle the form submission
            temp_view = QWebEngineView(self)
            temp_view.urlChanged.connect(lambda url: self.handle_form_submission(url, temp_view))
            return temp_view
        return None
    
    def handle_form_submission(self, url, view):
        """Handle form submissions to our custom URL scheme"""
        url_string = url.toString()
        if url_string.startswith("pyqt://export_pdf"):
            # Get the form data
            view.page().toHtml(lambda html: self.process_pdf_export(html, view))
            return True
        return False
    
    def process_pdf_export(self, html, view):
        """Process the PDF export request"""
        try:
            # Extract the export_data from the HTML
            import re
            from PyQt5.QtPrintSupport import QPrinter
            import json
            import os
            
            # Extract the JSON data from the form
            match = re.search(r'name="export_data" value="([^"]+)"', html)
            if match:
                # Decode the JSON data (need to handle escaped quotes)
                json_str = match.group(1).replace('&quot;', '"')
                export_data = json.loads(json_str)
                
                # Get the Downloads folder path
                downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
                if not os.path.exists(downloads_path):
                    # If Downloads folder doesn't exist, create it or use Desktop
                    if os.path.exists(os.path.join(os.path.expanduser('~'), 'Desktop')):
                        downloads_path = os.path.join(os.path.expanduser('~'), 'Desktop')
                    else:
                        downloads_path = os.path.expanduser('~')  # Fallback to user directory
                
                # Generate a unique filename using timestamp
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = export_data.get('path', f'AISAT_Transaction_History_{timestamp}.pdf')
                file_path = os.path.join(downloads_path, filename)
                
                # If a file with the same name already exists, add a number to make it unique
                base_name = os.path.splitext(file_path)[0]
                extension = os.path.splitext(file_path)[1]
                counter = 1
                while os.path.exists(file_path):
                    file_path = f"{base_name}_{counter}{extension}"
                    counter += 1
                
                # Create a printer object
                printer = QPrinter(QPrinter.HighResolution)
                printer.setOutputFormat(QPrinter.PdfFormat)
                printer.setOutputFileName(file_path)
                
                # Create a new WebEngineView to render the PDF content
                from PyQt5.QtCore import QSize
                pdf_view = QWebEngineView()
                pdf_view.resize(QSize(1024, 768))  # Set a reasonable size
                
                # Generate HTML content for the PDF
                html_content = self.generate_pdf_html(export_data)
                pdf_view.setHtml(html_content)
                
                # When the page is loaded, print it to PDF
                pdf_view.loadFinished.connect(
                    lambda ok: self.print_to_pdf(ok, pdf_view, printer, file_path)
                )
                
                # Clean up the temporary view
                view.deleteLater()
            else:
                print("Could not extract export data from form submission")
                view.deleteLater()
        except Exception as e:
            print(f"Error processing PDF export: {e}")
            view.deleteLater()
    
    def print_to_pdf(self, ok, view, printer, file_path):
        """Print the view to PDF"""
        if ok:
            def pdf_done(success):
                if success:
                    print(f"PDF saved successfully to {file_path}")
                    # Get the folder name for a cleaner message
                    import os
                    folder_name = os.path.dirname(file_path)
                    file_name = os.path.basename(file_path)
                    
                    # Check if it's in Downloads or Desktop folder
                    if "Downloads" in folder_name:
                        folder_display = "Downloads folder"
                    elif "Desktop" in folder_name:
                        folder_display = "Desktop"
                    else:
                        folder_display = folder_name
                        
                    QMessageBox.information(
                        self, 
                        "PDF Export", 
                        f"PDF report '{file_name}' has been saved to your {folder_display}."
                    )
                else:
                    print("PDF printing failed")
                    QMessageBox.warning(
                        self, 
                        "PDF Export Failed", 
                        "Failed to generate the PDF report."
                    )
                view.deleteLater()
            
            # Print to PDF
            view.page().printToPdf(file_path, printer.pageLayout())
            view.page().pdfPrintingFinished.connect(pdf_done)
        else:
            print("Page loading failed")
            view.deleteLater()
    
    def generate_pdf_html(self, export_data):
        """Generate HTML content for the PDF"""
        title = export_data.get('title', 'Transaction History')
        filters = export_data.get('filters', {})
        stats = export_data.get('stats', '')
        transactions = export_data.get('transactions', [])
        
        # Format date filters
        date_from = filters.get('dateFrom', '')
        date_to = filters.get('dateTo', '')
        status = filters.get('status', '')
        payment_type = filters.get('paymentType', '')
        
        # Generate HTML
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>{title}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    color: #333;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .header h1 {{
                    color: #001489;
                    margin-bottom: 10px;
                }}
                .header p {{
                    margin: 5px 0;
                    color: #666;
                }}
                .filter-info {{
                    margin: 20px 0;
                    padding: 10px;
                    background-color: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 4px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 30px;
                }}
                th, td {{
                    padding: 10px;
                    text-align: left;
                    border: 1px solid #ddd;
                }}
                th {{
                    background-color: #001489;
                    color: white;
                }}
                tr:nth-child(even) {{
                    background-color: #f2f2f2;
                }}
                tr.approved {{
                    background-color: #def7ec;
                }}
                tr.rejected {{
                    background-color: #fde8e8;
                }}
                .stats-section {{
                    margin-bottom: 30px;
                }}
                .stats-section h2 {{
                    color: #001489;
                    border-bottom: 1px solid #ddd;
                    padding-bottom: 10px;
                }}
                .footer {{
                    margin-top: 50px;
                    text-align: center;
                    font-size: 12px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{title}</h1>
                <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="filter-info">
                <strong>Filters Applied:</strong>
                {f"<p>From Date: {date_from}</p>" if date_from else ""}
                {f"<p>To Date: {date_to}</p>" if date_to else ""}
                {f"<p>Status: {status}</p>" if status else ""}
                {f"<p>Payment Type: {payment_type}</p>" if payment_type else ""}
                {f"<p>No filters applied</p>" if not any([date_from, date_to, status, payment_type]) else ""}
            </div>
            
            <div class="stats-section">
                <h2>Statistics</h2>
                {stats}
            </div>
            
            <h2>Transaction List</h2>
            <table>
                <thead>
                    <tr>
                        <th>Date/Time</th>
                        <th>Request ID</th>
                        <th>ID Number</th>
                        <th>Name</th>
                        <th>Level</th>
                        <th>Payment</th>
                        <th>Status</th>
                        <th>Processed By</th>
                        <th>Notes</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        # Add transaction rows
        if transactions:
            for trans in transactions:
                # Format date nicely
                formatted_date = 'N/A'
                if trans.get('action_date'):
                    try:
                        date = datetime.fromisoformat(trans['action_date'].replace('Z', '+00:00'))
                        formatted_date = date.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        formatted_date = trans['action_date']
                
                status_class = trans.get('status', '')
                html += f"""
                    <tr class="{status_class}">
                        <td>{formatted_date}</td>
                        <td>{trans.get('request_id', '')}</td>
                        <td>{trans.get('idno', '')}</td>
                        <td>{trans.get('name', '')}</td>
                        <td>{trans.get('level', '')}</td>
                        <td>{trans.get('payment', '')}</td>
                        <td>{trans.get('status', '')}</td>
                        <td>{trans.get('admin_name', '')}</td>
                        <td>{trans.get('notes', '')}</td>
                    </tr>
                """
        else:
            html += """
                <tr>
                    <td colspan="9" style="text-align: center;">No transactions found</td>
                </tr>
            """
        
        # Close the HTML
        html += f"""
                </tbody>
            </table>
            
            <div class="footer">
                <p>AISAT College Registral Services</p>
                <p>This report contains {len(transactions) if transactions else 0} transactions</p>
            </div>
        </body>
        </html>
        """
        
        return html

    def _on_load_finished(self, ok):
        if ok:
            # This JavaScript code runs inside the loaded web page.
            # It sets the userToken and baseUrl in localStorage to allow API calls
            js_code = f"""
            localStorage.setItem('userToken', '{self.token}');
            localStorage.setItem('baseUrl', 'https://jimboyaczon.pythonanywhere.com');
            
            // Override fetch to handle CORS issues when loading from filesystem
            const originalFetch = window.fetch;
            window.fetch = function(url, options) {{
                // If the URL is relative or doesn't have http(s), add the base URL
                if (!url.startsWith('http')) {{
                    // Handle paths that start with /
                    if (url.startsWith('/')) {{
                        url = 'https://jimboyaczon.pythonanywhere.com' + url;
                    }} else if (url.startsWith('./api') || url.startsWith('api')) {{
                        // Handle relative API paths
                        url = 'https://jimboyaczon.pythonanywhere.com/' + url.replace('./', '');
                    }}
                }}
                
                // Ensure options exists
                options = options || {{}};
                
                // Add Authorization header if token exists
                if (localStorage.getItem('userToken')) {{
                    options.headers = options.headers || {{}};
                    options.headers['Authorization'] = 'Bearer ' + localStorage.getItem('userToken');
                }}
                
                return originalFetch(url, options);
            }};

            // Bridge mechanism for sharing data between WebEngineView instances
            if (window.location.href.includes('ads.html')) {{
                // For ads.html, add methods to save announcements to a file
                window.saveAnnouncementsToFile = function(data) {{
                    console.log('Saving announcements to file and tvDisplayAnnouncements:', data);
                    
                    // Use fetch to call a custom endpoint
                    fetch('https://jimboyaczon.pythonanywhere.com/api/save_announcements', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer ' + localStorage.getItem('userToken')
                        }},
                        body: JSON.stringify({{ announcements: data }})
                    }})
                    .then(response => response.json())
                    .then(result => {{
                        console.log('Announcements saved to file successfully:', result);
                        
                        // Also ensure tvDisplayAnnouncements is set
                        localStorage.setItem('tvDisplayAnnouncements', JSON.stringify(data));
                        console.log('tvDisplayAnnouncements explicitly set in localStorage');
                    }})
                    .catch(error => {{
                        console.error('Failed to save announcements to file:', error);
                    }});
                }};

                // Override localStorage setItem for aisatAnnouncements
                const originalSetItem = localStorage.setItem;
                localStorage.setItem = function(key, value) {{
                    // Call the original function first
                    originalSetItem.call(localStorage, key, value);
                    
                    // If this is announcement data, also save to file and set tvDisplayAnnouncements
                    if (key === 'aisatAnnouncements') {{
                        console.log('Syncing aisatAnnouncements to shared file and tvDisplayAnnouncements');
                        try {{
                            const data = JSON.parse(value);
                            
                            // Also set tvDisplayAnnouncements to ensure it's available for tv_display.html
                            originalSetItem.call(localStorage, 'tvDisplayAnnouncements', value);
                            console.log('tvDisplayAnnouncements set from aisatAnnouncements');
                            
                            // Save to file
                            window.saveAnnouncementsToFile(data);
                        }} catch (error) {{
                            console.error('Error parsing announcements data:', error);
                        }}
                    }}
                }};
                
                // Add a sync button to force synchronization
                setTimeout(function() {{
                    try {{
                        const refreshBtn = document.getElementById('refresh-ads-btn');
                        if (refreshBtn && !document.getElementById('sync-tv-btn')) {{
                            const syncBtn = document.createElement('button');
                            syncBtn.id = 'sync-tv-btn';
                            syncBtn.className = 'btn btn-sm btn-info ml-2';
                            syncBtn.innerHTML = '<i class="fas fa-sync"></i> Sync to TV';
                            syncBtn.onclick = function() {{
                                const announcements = JSON.parse(localStorage.getItem('aisatAnnouncements') || '[]');
                                window.saveAnnouncementsToFile(announcements);
                                alert('Announcements synced to TV display!');
                            }};
                            refreshBtn.parentNode.appendChild(syncBtn);
                            console.log('Added Sync to TV button');
                        }}
                    }} catch (e) {{
                        console.error('Error adding sync button:', e);
                    }}
                }}, 2000);
            }} else if (window.location.href.includes('tv_display.html')) {{
                // For tv_display.html, add method to load from file
                window.loadAnnouncementsFromFile = function() {{
                    console.log('TV Display: Loading announcements from file');
                    
                    // Use fetch to get the data
                    fetch('https://jimboyaczon.pythonanywhere.com/api/get_announcements')
                        .then(response => response.json())
                        .then(data => {{
                            console.log('Loaded announcements from file:', data);
                            if (data && data.announcements && data.announcements.length > 0) {{
                                console.log('Found ' + data.announcements.length + ' announcements from file');
                                
                                // Store in localStorage
                                localStorage.setItem('tvDisplayAnnouncements', JSON.stringify(data.announcements));
                                
                                // Force refresh by calling loadAnnouncements directly
                                if (window.loadAnnouncements) {{
                                    console.log('Calling loadAnnouncements() to refresh display');
                                    window.loadAnnouncements();
                                }} else if (window.refreshAnnouncements) {{
                                    console.log('Calling refreshAnnouncements()');
                                    window.refreshAnnouncements(data.announcements);
                                }}
                            }} else {{
                                console.log('No announcements found in file, checking localStorage');
                                
                                // Check if we have any in aisatAnnouncements
                                const localAnnouncements = localStorage.getItem('aisatAnnouncements');
                                if (localAnnouncements) {{
                                    console.log('Found announcements in aisatAnnouncements, using those');
                                    localStorage.setItem('tvDisplayAnnouncements', localAnnouncements);
                                    
                                    if (window.loadAnnouncements) {{
                                        window.loadAnnouncements();
                                    }}
                                }}
                            }}
                        }})
                        .catch(error => {{
                            console.error('Failed to load announcements from file:', error);
                        }});
                }};
                
                // Add a helper function to fetch admin settings without authentication
                window.fetchAdminSettings = function(adminId) {{
                    console.log('TV Display: Fetching admin settings for admin ID:', adminId);
                    fetch('https://jimboyaczon.pythonanywhere.com/api/tv/get-admin-settings?admin_id=' + adminId)
                        .then(response => response.json())
                        .then(data => {{
                            console.log('Loaded admin settings from API:', data);
                            if (data && data.settings && data.settings.filter_settings) {{
                                // Store in localStorage with admin-specific key
                                localStorage.setItem('adminFilterSettings_' + adminId, JSON.stringify(data.settings.filter_settings));
                                console.log('Saved admin filter settings to localStorage');
                                
                                // Also update global settings
                                localStorage.setItem('adminFilterSettings', JSON.stringify(data.settings.filter_settings));
                            }}
                        }})
                        .catch(error => {{
                            console.error('Failed to load admin settings:', error);
                        }});
                }};
                
                // Define refreshAnnouncements if it doesn't exist
                if (!window.refreshAnnouncements) {{
                    window.refreshAnnouncements = function(data) {{
                        console.log('Refreshing with data:', data);
                        if (window.loadAnnouncements) {{
                            window.loadAnnouncements();
                        }}
                    }};
                }}
                
                // Load announcements from file immediately
                window.loadAnnouncementsFromFile();
                
                // Refresh more frequently for testing
                setInterval(window.loadAnnouncementsFromFile, 5000);
            }}
            """
            
            # Set theme if provided
            if self.theme:
                js_code += f"localStorage.setItem('adminTheme', '{self.theme}'); document.documentElement.setAttribute('data-theme', '{self.theme}');"
            
            # Use a callback to ensure the token is set before making any API calls
            def token_set_callback(result):
                if self.initial_js_call:
                    self.page().runJavaScript(f"{self.initial_js_call}();")
            
            self.page().runJavaScript(js_code, token_set_callback)
    
    def update_theme(self, theme):
        """Update the theme of the web view."""
        self.theme = theme
        js_code = f"localStorage.setItem('adminTheme', '{theme}'); document.documentElement.setAttribute('data-theme', '{theme}');"
        self.page().runJavaScript(js_code)

class AddUserDialog(QDialog):
    """A dialog for admins to create a new user."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New User")

        # Create input widgets
        self.idno_input = QLineEdit()
        self.name_input = QLineEdit()
        self.email_input = QLineEdit()
        self.level_options = ["College", "SHS"]
        self.level_input = QLineEdit()
        self.level_input.setText(self.level_options[0])  # Default to College
        self.cell_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)

        # Layout the form
        form_layout = QFormLayout()
        form_layout.addRow("ID Number:", self.idno_input)
        form_layout.addRow("Full Name:", self.name_input)
        form_layout.addRow("Email:", self.email_input)
        form_layout.addRow("Level (College/SHS):", self.level_input)
        form_layout.addRow("Contact Number:", self.cell_input)
        form_layout.addRow("Password:", self.password_input)

        # Create OK and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        main_layout = QVBoxLayout()
        main_layout.addLayout(form_layout)
        main_layout.addWidget(button_box)
        self.setLayout(main_layout)

    def get_data(self):
        """Returns the data entered in the form as a dictionary."""
        return {
            "idno": self.idno_input.text(),
            "name": self.name_input.text(),
            "email": self.email_input.text(),
            "level": self.level_input.text(),
            "cell": self.cell_input.text(),
            "password": self.password_input.text(),
        }

class ThemeSwitch(QWidget):
    """A custom widget for theme switching."""
    def __init__(self, admin_panel=None):
        super(ThemeSwitch, self).__init__()
        self.is_dark = False
        self.admin_panel = admin_panel
        
        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Toggle switch
        self.switch = QCheckBox()
        self.switch.setStyleSheet("""
            QCheckBox {
                background-color: transparent;
            }
            QCheckBox::indicator {
                width: 36px;
                height: 18px;
                border-radius: 9px;
                background-color: #3b3842;
            }
            QCheckBox::indicator:checked {
                background-color: #78dce8;
            }
            QCheckBox::indicator:unchecked {
                background-color: #3498db;
            }
        """)
        
        # Theme label
        self.theme_label = QLabel("Light")
        self.theme_label.setStyleSheet("color: white; font-size: 14px;")
        
        # Add widgets to layout
        layout.addWidget(self.switch)
        layout.addWidget(self.theme_label)
        
        # Connect signal
        self.switch.stateChanged.connect(self.on_state_changed)
        
    def on_state_changed(self, state):
        self.is_dark = (state == Qt.CheckState.Checked)
        if self.admin_panel:
            self.admin_panel.on_theme_changed(self.is_dark)
        
        # Update label
        self.theme_label.setText("            Dark" if self.is_dark else "            Light")
        
    def set_theme(self, is_dark):
        self.is_dark = is_dark
        self.switch.setChecked(is_dark)
        self.theme_label.setText("            Dark" if is_dark else "            Light")

class AdminPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("AISAT", "AdminPanel")
        
        # Initialize UI elements as None
        self.left_panel = None
        self.right_panel = None
        self.logo_label = None
        self.admin_label = None
        self.separator = None
        self.theme_label = None
        self.theme_switch = None
        self.sign_out_button = None
        self.welcome_widget = None
        self.buttons = {}
        
        # Check if token exists and is valid before showing UI
        is_valid, self.admin_name = check_session(self.settings)
        if not is_valid:
            login_dialog = LoginDialog()
            if login_dialog.exec_() == QDialog.Accepted:
                # On successful login, get the admin name from the dialog itself.
                # The token is already saved in settings by the dialog.
                self.admin_name = login_dialog.get_admin_name()
                self.initUI()
            else:
                # User cancelled login, exit application
                sys.exit()
        else:
            # Session was already valid, init UI
            self.initUI()
        
    def initUI(self):
        # Get current theme setting
        self.current_theme = self.settings.value("theme", "light")
        
        # Set window properties
        self.setWindowTitle('AISAT Admin Panel')
        self.setGeometry(100, 100, 1200, 800)
        
        # Set admin as active when application starts
        self.set_admin_active()
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create left panel (sidebar)
        self.left_panel = QFrame()
        self.left_panel.setFrameShape(QFrame.StyledPanel)
        self.left_panel.setFixedWidth(250)
        
        # Create right panel (content area)
        self.right_panel = QFrame()
        self.right_panel.setFrameShape(QFrame.StyledPanel)
        
        # Add panels to main layout
        main_layout.addWidget(self.left_panel)
        main_layout.addWidget(self.right_panel)
        
        # Set up the left panel layout
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        left_layout.setContentsMargins(10, 20, 10, 20)
        left_layout.setSpacing(10)
        
        # Add logo to the left panel
        self.logo_label = QLabel()
        pixmap = QPixmap("img/aisat.png")
        # Scale the image to fit the sidebar width while maintaining aspect ratio
        scaled_pixmap = pixmap.scaled(220, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.logo_label.setPixmap(scaled_pixmap)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.logo_label)
        
        # Add admin name
        self.admin_label = QLabel(f"Welcome, {self.admin_name}")
        self.admin_label.setStyleSheet("font-size: 14px;")
        self.admin_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.admin_label)
        
        # Add separator
        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setFixedHeight(2)
        left_layout.addWidget(self.separator)
        left_layout.addSpacing(20)
        
        # Menu items
        menu_items = [
            {"name": "Pending Request", "icon": "note.png"},
            {"name": "Rejected Request", "icon": "note.png"},
            {"name": "Scheduled Request", "icon": "note.png"},
            {"name": "Schedule", "icon": "note.png"},
            {"name": "Users", "icon": "people.png"},
            {"name": "Priority Users", "icon": "prio.png"},
            {"name": "Request Ticket", "icon": "note.png"},
            {"name": "Transaction History", "icon": "note.png"},
            {"name": "Announcement Management", "icon": "note.png"},
            {"name": "Admin Settings", "icon": "gear.png"},
            {"name": "TV Display", "icon": "note.png"}
        ]
        
        # Add buttons for each menu item
        self.buttons = {}
        for item in menu_items:
            button = QPushButton(item["name"])
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            left_layout.addWidget(button)
            self.buttons[item["name"]] = button
            
            # Connect button to slot
            button.clicked.connect(lambda checked, name=item["name"]: self.menu_item_clicked(name))
        
        # Add spacer at the bottom
        left_layout.addStretch()
        
        # Add theme switch
        theme_container = QHBoxLayout()
        self.theme_label = QLabel("Theme:")
        theme_container.addWidget(self.theme_label)
        
        self.theme_switch = ThemeSwitch(self)
        theme_container.addWidget(self.theme_switch)
        theme_container.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        left_layout.addLayout(theme_container)
        
        # Initialize theme switch state
        self.theme_switch.set_theme(self.current_theme == "dark")
        
        # Add sign out button
        self.sign_out_button = QPushButton("Sign Out")
        self.sign_out_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sign_out_button.clicked.connect(self.logout)
        left_layout.addWidget(self.sign_out_button)
        
        # Add content to right panel using a QStackedWidget
        self.content_stack = QStackedWidget()
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.content_stack)

        # Create the content widgets
        self.welcome_widget = QLabel("Select an option from the menu.")
        self.welcome_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_stack.addWidget(self.welcome_widget)

        # Create and add the pending requests web view
        self.pending_request_view = self.create_pending_request_view()
        self.content_stack.addWidget(self.pending_request_view)
        
        # Create and add the schedule web view
        self.schedule_view = self.create_schedule_view()
        self.content_stack.addWidget(self.schedule_view)
        
        # Apply initial theme
        self.apply_theme_styles(self.current_theme)
        
        # Show the window
        self.show()

    def apply_theme_styles(self, theme):
        """Apply theme styles to the UI components."""
        colors = THEME_COLORS[theme]
        
        # Left panel
        if self.left_panel:
            self.left_panel.setStyleSheet(f"background-color: {colors['sidebar_bg']};")
        
        # Right panel
        if self.right_panel:
            self.right_panel.setStyleSheet(f"background-color: {colors['bg_primary']};")
        
        # Admin label
        if self.admin_label:
            self.admin_label.setStyleSheet(f"color: {colors['sidebar_text']}; font-size: 14px;")
        
        # Separator
        if self.separator:
            self.separator.setStyleSheet(f"background-color: {colors['border_color']};")
        
        # Theme label
        if self.theme_label:
            self.theme_label.setStyleSheet(f"color: {colors['sidebar_text']}; font-size: 14px;")
        
        # Buttons - always white text in sidebar
        button_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {colors['sidebar_text']};
                text-align: left;
                padding: 12px;
                border: none;
                border-radius: 5px;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: {colors['sidebar_hover']};
            }}
            QPushButton:pressed {{
                background-color: {colors['sidebar_active']};
            }}
        """
        
        for button in self.buttons.values():
            if button:
                button.setStyleSheet(button_style)
        
        # Sign out button
        if self.sign_out_button:
            self.sign_out_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: #e74c3c;
                    color: white;
                    padding: 12px;
                    border: none;
                    border-radius: 5px;
                    font-size: 16px;
                }}
                QPushButton:hover {{
                    background-color: #c0392b;
                }}
            """)
        
        # Welcome widget
        if self.welcome_widget:
            self.welcome_widget.setStyleSheet(f"color: {colors['text_primary']}; font-size: 18px;")

    def create_pending_request_view(self):
        token = self.settings.value("auth_token", "")
        if not token:
            return QLabel("Authentication error. Please log in again.")

        web_view = WebEngineView(token, initial_js_call="fetchPendingRequests", theme=self.current_theme)
        web_view.setUrl(QUrl.fromLocalFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sideload/pending_request.html")))

        return web_view

    def create_rejected_request_view(self):
        token = self.settings.value("auth_token", "")
        if not token:
            return QLabel("Authentication error. Please log in again.")

        web_view = WebEngineView(token, initial_js_call="fetchRejectedRequests", theme=self.current_theme)
        web_view.setUrl(QUrl.fromLocalFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sideload/rejected_request.html")))

        return web_view

    def create_schedule_view(self):
        token = self.settings.value("auth_token", "")
        if not token:
            return QLabel("Authentication error. Please log in again.")

        web_view = WebEngineView(token, initial_js_call="renderCalendar", theme=self.current_theme)
        web_view.setUrl(QUrl.fromLocalFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sideload/calendar.html")))
        
        return web_view

    def create_admin_settings_view(self):
        token = self.settings.value("auth_token", "")
        if not token:
            return QLabel("Authentication error. Please log in again.")

        web_view = WebEngineView(token, theme=self.current_theme)
        web_view.setUrl(QUrl.fromLocalFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sideload/admin_settings.html")))
        
        return web_view

    def create_users_view(self):
        token = self.settings.value("auth_token", "")
        if not token:
            return QLabel("Authentication error. Please log in again.")

        web_view = WebEngineView(token, initial_js_call="fetchUsers", theme=self.current_theme)
        web_view.setUrl(QUrl.fromLocalFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sideload/users.html")))
        
        return web_view

    def create_scheduled_request_view(self):
        token = self.settings.value("auth_token", "")
        if not token:
            return QLabel("Authentication error. Please log in again.")

        web_view = WebEngineView(token, initial_js_call="fetchScheduledRequests", theme=self.current_theme)
        web_view.setUrl(QUrl.fromLocalFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sideload/scheduled_request.html")))

        return web_view

    def create_request_ticket_view(self):
        token = self.settings.value("auth_token", "")
        if not token:
            return QLabel("Authentication error. Please log in again.")

        web_view = WebEngineView(token, theme=self.current_theme)
        web_view.setUrl(QUrl.fromLocalFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sideload/request.html")))
        
        return web_view

    def create_priorities_view(self):
        token = self.settings.value("auth_token", "")
        if not token:
            return QLabel("Authentication error. Please log in again.")

        web_view = WebEngineView(token, theme=self.current_theme)
        web_view.setUrl(QUrl.fromLocalFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sideload/priorities.html")))
        
        return web_view

    def create_ads_view(self):
        token = self.settings.value("auth_token", "")
        if not token:
            return QLabel("Authentication error. Please log in again.")

        web_view = WebEngineView(token, theme=self.current_theme)
        web_view.setUrl(QUrl.fromLocalFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sideload/ads.html")))
        
        return web_view

    def create_transaction_history_view(self):
        token = self.settings.value("auth_token", "")
        if not token:
            return QLabel("Authentication error. Please log in again.")

        web_view = WebEngineView(token, theme=self.current_theme)
        web_view.setUrl(QUrl.fromLocalFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sideload/transachistory.html")))
        
        return web_view

    def create_tv_display_view(self):
        token = self.settings.value("auth_token", "")
        if not token:
            return QLabel("Authentication error. Please log in again.")

        # Create web view
        web_view = WebEngineView(token, initial_js_call="fetchAdminsAndQueues", theme=self.current_theme)
        
        # Configure video playback and announcement loading via JavaScript
        js_config = """
        // Enable video autoplay
        document.addEventListener('DOMContentLoaded', function() {
            console.log('TV Display: DOM content loaded, configuring video playback');
            
            // Enable autoplay for all videos
            function setupVideos() {
                document.querySelectorAll('video').forEach(function(video) {
                    video.setAttribute('autoplay', true);
                    video.setAttribute('muted', true);
                    video.setAttribute('playsinline', true);
                    video.setAttribute('preload', 'auto');
                    
                    // Force play on load
                    video.addEventListener('loadeddata', function() {
                        video.play().catch(function(e) {
                            console.error('Video play error:', e);
                        });
                    });
                });
                console.log('Video autoplay configuration applied');
            }
            
            // Setup video elements initially
            setupVideos();
            
            // And also set up a MutationObserver to handle dynamically added videos
            var observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.addedNodes && mutation.addedNodes.length > 0) {
                        setupVideos();
                    }
                });
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
            
            // Force load announcements from localStorage
            console.log('Checking for announcements in localStorage');
            var announcements = localStorage.getItem('aisatAnnouncements') || localStorage.getItem('tvDisplayAnnouncements');
            console.log('Found announcements:', announcements ? 'YES' : 'NO');
            
            // If window.loadAnnouncements exists, call it to refresh the display
            if (window.loadAnnouncements) {
                console.log('Calling loadAnnouncements function');
                window.loadAnnouncements();
                
                // Also set up periodic refresh
                setInterval(window.loadAnnouncements, 5000);
            }
        });
        """
        
        # Set URL first, then inject the JavaScript after page load
        web_view.setUrl(QUrl.fromLocalFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tv_display.html")))
        web_view.loadFinished.connect(lambda ok: web_view.page().runJavaScript(js_config) if ok else None)
        
        return web_view

    def on_theme_changed(self, is_dark):
        """Handle theme change."""
        theme = "dark" if is_dark else "light"
        self.current_theme = theme
        
        # Save theme setting
        self.settings.setValue("theme", theme)
        
        # Apply theme styles to UI components
        self.apply_theme_styles(theme)
        
        # Update all web views
        for attr_name in dir(self):
            if attr_name.endswith('_view') and hasattr(self, attr_name):
                view = getattr(self, attr_name)
                if isinstance(view, WebEngineView):
                    view.update_theme(theme)

    def menu_item_clicked(self, item_name):
        print(f"Clicked: {item_name}")
        
        if item_name == "Pending Request":
            self.content_stack.setCurrentWidget(self.pending_request_view)
        elif item_name == "Rejected Request":
            # Create the rejected request view if it doesn't exist
            if not hasattr(self, 'rejected_request_view'):
                self.rejected_request_view = self.create_rejected_request_view()
                self.content_stack.addWidget(self.rejected_request_view)
            self.content_stack.setCurrentWidget(self.rejected_request_view)
        elif item_name == "Scheduled Request":
            # Create the scheduled request view if it doesn't exist
            if not hasattr(self, 'scheduled_request_view'):
                self.scheduled_request_view = self.create_scheduled_request_view()
                self.content_stack.addWidget(self.scheduled_request_view)
            self.content_stack.setCurrentWidget(self.scheduled_request_view)
        elif item_name == "Schedule":
            self.content_stack.setCurrentWidget(self.schedule_view)
        elif item_name == "Users":
            # Create the users view if it doesn't exist
            if not hasattr(self, 'users_view'):
                self.users_view = self.create_users_view()
                self.content_stack.addWidget(self.users_view)
            self.content_stack.setCurrentWidget(self.users_view)
        elif item_name == "Admin Settings":
            # Create the admin settings view if it doesn't exist
            if not hasattr(self, 'admin_settings_view'):
                self.admin_settings_view = self.create_admin_settings_view()
                self.content_stack.addWidget(self.admin_settings_view)
            self.content_stack.setCurrentWidget(self.admin_settings_view)
        elif item_name == "Request Ticket":
            # Create the request ticket view if it doesn't exist
            if not hasattr(self, 'request_ticket_view'):
                self.request_ticket_view = self.create_request_ticket_view()
                self.content_stack.addWidget(self.request_ticket_view)
            self.content_stack.setCurrentWidget(self.request_ticket_view)
        elif item_name == "Priority Users":
            # Create the priorities view if it doesn't exist
            if not hasattr(self, 'priorities_view'):
                self.priorities_view = self.create_priorities_view()
                self.content_stack.addWidget(self.priorities_view)
            self.content_stack.setCurrentWidget(self.priorities_view)
        elif item_name == "Announcement Management":
            # Create the ads view if it doesn't exist
            if not hasattr(self, 'ads_view'):
                self.ads_view = self.create_ads_view()
                self.content_stack.addWidget(self.ads_view)
            self.content_stack.setCurrentWidget(self.ads_view)
        elif item_name == "Transaction History":
            # Create the transaction history view if it doesn't exist
            if not hasattr(self, 'transaction_history_view'):
                self.transaction_history_view = self.create_transaction_history_view()
                self.content_stack.addWidget(self.transaction_history_view)
            self.content_stack.setCurrentWidget(self.transaction_history_view)
        elif item_name == "TV Display":
            # Create the TV display view if it doesn't exist
            if not hasattr(self, 'tv_display_view'):
                self.tv_display_view = self.create_tv_display_view()
                self.content_stack.addWidget(self.tv_display_view)
            self.content_stack.setCurrentWidget(self.tv_display_view)
        elif item_name == "Add User":
            self.add_user()
        else:
            # Default to the welcome message for other buttons for now
            self.content_stack.setCurrentWidget(self.welcome_widget)
    
    def add_user(self):
        """Opens the Add User dialog and handles the user creation."""
        dialog = AddUserDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            user_data = dialog.get_data()
            
            if not all(user_data.values()): # A simpler way to check all fields
                QMessageBox.warning(self, "Input Error", "All fields are required.")
                return

            # Validate the level is one of the allowed values
            if user_data["level"] not in ["College", "SHS"]:
                QMessageBox.warning(self, "Input Error", "Level must be either 'College' or 'SHS'.")
                return

            token = self.settings.value("auth_token", "")
            if not token:
                QMessageBox.critical(self, "Authentication Error", "Could not retrieve session token. Please log in again.")
                self.logout()  # Force logout to restart authentication
                return

            try:
                # Using the create_public_user endpoint to create a regular user (not an admin)
                response = requests.post(
                    f"{API_BASE_URL}/api/auth/create_public_user",
                    json=user_data,
                    timeout=10
                )
                
                if response.status_code == 201:
                    QMessageBox.information(self, "Success", "User registered successfully.")
                elif response.status_code == 401:
                    QMessageBox.critical(self, "Authentication Error", "Your session has expired. Please log in again.")
                    self.logout()  # Force logout to restart authentication
                else:
                    error_msg = response.json().get("error", "An unknown error occurred.")
                    QMessageBox.critical(self, "Registration Failed", error_msg)
            except requests.RequestException as e:
                QMessageBox.critical(self, "Connection Error", f"Could not connect to server: {e}")

    def set_admin_active(self):
        """Set the current admin as active in the database."""
        token = self.settings.value("auth_token", "")
        if not token:
            print("No auth token found, cannot set admin as active")
            return
            
        try:
            # Call the API to set admin as active
            response = requests.post(
                f"{API_BASE_URL}/api/admin/update-active-status",
                headers={"Authorization": f"Bearer {token}"},
                json={"is_active": "yes"},
                timeout=10
            )
            
            if response.status_code == 200:
                print("Admin set as active successfully")
            else:
                print(f"Failed to set admin as active: {response.status_code}")
        except Exception as e:
            print(f"Error setting admin as active: {e}")

    def logout(self):
        """Log out the current user"""
        reply = QMessageBox.question(
            self, 
            "Confirm Logout", 
            "Are you sure you want to logout?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Set admin as inactive before logging out
            self.set_admin_inactive()
            
            # Clear the token
            self.settings.remove("auth_token")
            
            # Restart the application
            QApplication.quit()
            os.execl(sys.executable, sys.executable, *sys.argv)
            
    def set_admin_inactive(self):
        """Set the current admin as inactive in the database."""
        token = self.settings.value("auth_token", "")
        if not token:
            return
            
        try:
            # First try the update-active-status endpoint with proper authentication
            response = requests.post(
                f"{API_BASE_URL}/api/admin/update-active-status",
                headers={"Authorization": f"Bearer {token}"},
                json={"is_active": "no"},
                timeout=10
            )
            
            if response.status_code == 200:
                print("Admin set as inactive successfully using authenticated endpoint")
            else:
                print(f"Failed to set admin as inactive with authenticated endpoint: {response.status_code}")
                
                # If that fails, try the direct set_admin_active endpoint as a fallback
                try:
                    # First get the admin ID
                    admin_response = requests.get(
                        f"{API_BASE_URL}/api/admin/profile",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=10
                    )
                    
                    if admin_response.status_code == 200:
                        admin_data = admin_response.json()
                        admin_id = admin_data.get("id")
                        
                        if admin_id:
                            # Use the direct endpoint as a fallback
                            direct_response = requests.get(
                                f"{API_BASE_URL}/api/set_admin_active?admin_id={admin_id}&is_active=no",
                                timeout=10
                            )
                            
                            if direct_response.status_code == 200:
                                print(f"Admin {admin_id} set as inactive successfully using direct endpoint")
                            else:
                                print(f"Failed to set admin as inactive with direct endpoint: {direct_response.status_code}")
                    else:
                        print(f"Failed to get admin profile: {admin_response.status_code}")
                except Exception as e:
                    print(f"Error using fallback method to set admin as inactive: {e}")
        except Exception as e:
            print(f"Error setting admin as inactive: {e}")
            
    def closeEvent(self, event):
        """Handle the window close event."""
        # Set admin as inactive when application closes
        print("Application closing - setting admin as inactive")
        self.set_admin_inactive()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = AdminPanel()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
