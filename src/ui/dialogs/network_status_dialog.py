"""Network status dialog for checking connectivity to various services."""

import threading

import customtkinter as ctk

from src.core.enums import NetworkStatus, ServiceType
from src.services.network.checker import check_all_services, check_internet_connection


class NetworkStatusDialog(ctk.CTkToplevel):
    """Dialog to show network connectivity status."""

    def __init__(self, parent) -> None:
        super().__init__(parent)

        # Initialize state
        self.parent = parent
        self.service_statuses = {
            service: NetworkStatus.UNKNOWN for service in ServiceType
        }

        # Set window properties
        self.title("Network Status")
        self.geometry("500x350")
        self.resizable(False, False)
        self.transient(parent)  # Make dialog modal-like
        self.grab_set()  # Make dialog modal

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        # Create main frame
        self.frame = ctk.CTkFrame(self)
        self.frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=20)

        # Title
        self.title_label = ctk.CTkLabel(
            self.frame,
            text="Network Connectivity Status",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.title_label.pack(pady=(0, 20))

        # Status labels for each service
        self.status_labels = {}
        for service in ServiceType:
            frame = ctk.CTkFrame(self.frame)
            frame.pack(fill=ctk.X, padx=10, pady=5)

            service_label = ctk.CTkLabel(
                frame,
                text=f"{service.name if hasattr(service, 'name') else str(service)}:",
                font=ctk.CTkFont(size=14, weight="bold"),
                width=100,
                anchor="w",
            )
            service_label.pack(side=ctk.LEFT, padx=10)

            status_label = ctk.CTkLabel(
                frame, text="Checking...", font=ctk.CTkFont(size=14), anchor="w"
            )
            status_label.pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=10)

            self.status_labels[service] = status_label

        # Button frame
        self.button_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.button_frame.pack(side=ctk.BOTTOM, fill=ctk.X, pady=20)

        # Retry button
        self.retry_button = ctk.CTkButton(
            self.button_frame, text="Retry Checks", command=self.check_connectivity
        )
        self.retry_button.pack(side=ctk.LEFT, padx=10)

        # Close button
        self.close_button = ctk.CTkButton(
            self.button_frame, text="Close", command=self.destroy
        )
        self.close_button.pack(side=ctk.RIGHT, padx=10)

        # Troubleshooting advice frame (initially hidden)
        self.advice_frame = None

        # Start checking connectivity
        self.check_connectivity()

    def check_connectivity(self):
        """Check connectivity to each service."""
        # Reset UI to show checking
        for service in ServiceType:
            self.service_statuses[service] = NetworkStatus.CHECKING
            self.status_labels[service].configure(text="Checking...", text_color="gray")

        # Disable retry button during check
        self.retry_button.configure(state="disabled")

        # Remove previous advice if it exists
        if self.advice_frame:
            self.advice_frame.destroy()
            self.advice_frame = None

        # Run checks in a background thread
        def check_worker():
            # First check internet connectivity
            internet_connected, error_msg = check_internet_connection()

            # Check individual services
            service_results = check_all_services()

            # Update service statuses
            any_error = False
            for service, (connected, error) in service_results.items():
                if connected:
                    self.service_statuses[service] = NetworkStatus.CONNECTED
                else:
                    self.service_statuses[service] = NetworkStatus.ERROR
                    any_error = True

            # Update UI from main thread
            self.after(
                0, lambda: self.update_status_display(service_results, any_error)
            )

        threading.Thread(target=check_worker, daemon=True).start()

    def update_status_display(
        self, service_results: Dict[ServiceType, tuple], any_error: bool
    ):
        """Update the status display with check results."""
        for service, (connected, error) in service_results.items():
            if service not in self.status_labels:
                continue

            if connected:
                self.status_labels[service].configure(
                    text="Connected", text_color="green"
                )
            else:
                self.status_labels[service].configure(
                    text=f"Error: {error}", text_color="red"
                )

        # Re-enable retry button
        self.retry_button.configure(state="normal")

        # Add advice if there are errors
        if any_error:
            self.add_troubleshooting_advice()

    def add_troubleshooting_advice(self):
        """Add troubleshooting advice to the dialog."""
        if self.advice_frame:
            return

        self.advice_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.advice_frame.pack(fill=ctk.X, padx=10, pady=(20, 10))

        advice_label = ctk.CTkLabel(
            self.advice_frame,
            text="Troubleshooting Steps:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        advice_label.pack(anchor="w")

        steps = [
            "1. Check your internet connection",
            "2. Make sure no firewall is blocking access",
            "3. Try restarting your network router",
            "4. If using a VPN, try disabling it temporarily",
            "5. Check if the service is down for everyone",
        ]

        for step in steps:
            step_label = ctk.CTkLabel(self.advice_frame, text=step, anchor="w")
            step_label.pack(anchor="w", padx=20)
