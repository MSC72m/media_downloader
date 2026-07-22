import threading
from typing import Any

import customtkinter as ctk

from src.core.enums import NetworkStatus, ServiceType
from src.services.network.checker import check_all_services, check_internet_connection
from src.ui import tokens
from src.ui.utils.theme_manager import ThemeManager
from src.ui.visual_system import GlassButton, GlassFrame, GradientButton, resolve_palette

from .base_dialog import BaseDialog


class NetworkStatusDialog(BaseDialog):
    """Dialog to show network connectivity status."""

    def __init__(self, parent: Any, theme_manager: ThemeManager | None = None) -> None:
        super().__init__(parent, title="Network Status", theme_manager=theme_manager)

        self.service_statuses = dict.fromkeys(ServiceType, NetworkStatus.UNKNOWN)
        self.status_labels: dict[ServiceType, ctk.CTkLabel] = {}
        self.advice_frame: GlassFrame | None = None

        self._create_widgets()
        self._finalize_init(
            preferred_width=520,
            preferred_height=560,
            min_width=460,
            min_height=400,
            modal=True,
        )
        self.check_connectivity()

    def _create_widgets(self) -> None:
        palette = resolve_palette(self._theme_manager)
        self.frame = GlassFrame(
            self.content_parent,
            theme_manager=self._theme_manager,
            elevation="raised",
        )
        self.frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.title_label = ctk.CTkLabel(
            self.frame,
            text="Network Connectivity Status",
            font=tokens.font("title"),
            text_color=palette.text,
        )
        self.title_label.pack(pady=(20, 12))

        self.status_frame = GlassFrame(
            self.frame,
            theme_manager=self._theme_manager,
            corner_radius=tokens.RADIUS_MD,
        )
        self.status_frame.pack(fill="x", padx=16, pady=8)

        for service in ServiceType:
            row = ctk.CTkFrame(self.status_frame, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=5)

            service_label = ctk.CTkLabel(
                row,
                text=f"{service.name if hasattr(service, 'name') else str(service)}:",
                font=tokens.font("body", weight="bold"),
                text_color=palette.text,
                width=110,
                anchor="w",
            )
            service_label.pack(side="left")

            status_label = ctk.CTkLabel(
                row,
                text="Checking...",
                font=tokens.font("body"),
                text_color=palette.text_muted,
                anchor="w",
            )
            status_label.pack(side="left", fill="x", expand=True, padx=(10, 0))
            self.status_labels[service] = status_label

        self.button_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.button_frame.pack(side="bottom", fill="x", padx=16, pady=16)

        self.retry_button = GradientButton(
            self.button_frame,
            text="Retry Checks",
            command=self.check_connectivity,
            theme_manager=self._theme_manager,
            width=140,
            height=tokens.CONTROL_H,
        )
        self.retry_button.pack(side="left")

        self.close_button = GlassButton(
            self.button_frame,
            text="Close",
            command=self.destroy,
            theme_manager=self._theme_manager,
            variant="secondary",
            width=100,
            height=tokens.CONTROL_H,
        )
        self.close_button.pack(side="right")

    def _on_theme_changed(self, _appearance: str, _color: str) -> None:
        self._apply_theme_colors()

    def _apply_theme_colors(self) -> None:
        palette = resolve_palette(self._theme_manager)
        self.title_label.configure(text_color=palette.text)

        for service, status in self.service_statuses.items():
            if service not in self.status_labels:
                continue
            if status == NetworkStatus.CHECKING:
                self.status_labels[service].configure(text_color=palette.text_muted)
            elif status == NetworkStatus.CONNECTED:
                self.status_labels[service].configure(text_color=palette.success)
            elif status == NetworkStatus.ERROR:
                self.status_labels[service].configure(text_color=palette.error)

    def check_connectivity(self) -> None:
        """Check connectivity to each service."""
        palette = resolve_palette(self._theme_manager)
        for service in ServiceType:
            self.service_statuses[service] = NetworkStatus.CHECKING
            self.status_labels[service].configure(
                text="Checking...",
                text_color=palette.text_muted,
            )

        self.retry_button.configure(state="disabled")

        if self.advice_frame:
            self.advice_frame.destroy()
            self.advice_frame = None

        def check_worker() -> None:
            check_internet_connection()
            service_results = check_all_services()

            any_error = False
            for service, (connected, _error) in service_results.items():
                if connected:
                    self.service_statuses[service] = NetworkStatus.CONNECTED
                else:
                    self.service_statuses[service] = NetworkStatus.ERROR
                    any_error = True

            if not self._dialog_destroyed:
                self.after(0, lambda: self.update_status_display(service_results, any_error))

        threading.Thread(target=check_worker, daemon=True).start()

    def update_status_display(
        self,
        service_results: dict[ServiceType, tuple[bool, str]],
        any_error: bool,
    ) -> None:
        """Update the status display with check results."""
        palette = resolve_palette(self._theme_manager)

        for service, (connected, error) in service_results.items():
            if service not in self.status_labels:
                continue

            if connected:
                self.service_statuses[service] = NetworkStatus.CONNECTED
                self.status_labels[service].configure(
                    text="Connected",
                    text_color=palette.success,
                )
            else:
                self.service_statuses[service] = NetworkStatus.ERROR
                self.status_labels[service].configure(
                    text=f"Error: {error}",
                    text_color=palette.error,
                )

        self.retry_button.configure(state="normal")

        if any_error:
            self.add_troubleshooting_advice()

    def add_troubleshooting_advice(self) -> None:
        """Add troubleshooting advice to the dialog."""
        if self.advice_frame:
            return

        palette = resolve_palette(self._theme_manager)
        self.advice_frame = GlassFrame(
            self.frame,
            theme_manager=self._theme_manager,
            corner_radius=tokens.RADIUS_MD,
        )
        self.advice_frame.pack(fill="x", padx=16, pady=(8, 4))

        advice_label = ctk.CTkLabel(
            self.advice_frame,
            text="Troubleshooting Steps",
            font=tokens.font("body", weight="bold"),
            text_color=palette.text,
            anchor="w",
        )
        advice_label.pack(fill="x", padx=14, pady=(10, 4))

        steps = [
            "1. Check your internet connection",
            "2. Make sure no firewall is blocking access",
            "3. Try restarting your network router",
            "4. If using a VPN, try disabling it temporarily",
            "5. Check if the service is down for everyone",
        ]
        for step in steps:
            step_label = ctk.CTkLabel(
                self.advice_frame,
                text=step,
                text_color=palette.text_secondary,
                anchor="w",
            )
            step_label.pack(fill="x", padx=14, pady=1)
