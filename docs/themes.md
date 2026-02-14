# Themes

Media Downloader uses a fully dynamic, file-based theme system. Themes are
plain JSON files that live in the `themes/` directory at the project root.
The app discovers them automatically at startup — no code changes required.

## Quick start — adding a custom theme

1. Copy any existing file in `themes/` (e.g. `themes/blue.json`) to a new
   file, for example `themes/sakura.json`.
2. Edit the `"name"`, `"emoji"`, and colour values.
3. Restart the app. Your theme appears in the colour-theme dropdown.

That's it.

## Theme file format

Every theme file is a JSON object with these top-level keys:

| Key     | Type   | Required | Description |
|---------|--------|----------|-------------|
| `name`  | string | yes      | Unique identifier (lowercase, no spaces). Must match the file stem — `cherry.json` should have `"name": "cherry"`. |
| `emoji` | string | yes      | Single emoji shown next to the theme name in the dropdown. |
| `light` | object | yes*     | Colour palette used in light mode. |
| `dark`  | object | yes*     | Colour palette used in dark mode. |

\* At least one of `light` or `dark` must be present. If you only provide one,
the theme will only be available in that appearance mode.

### Palette properties

Each mode object (`light` / `dark`) contains colour tokens. Values are either
a single hex string or a two-element array `[primary, secondary]`.

| Token                  | Format            | Used for |
|------------------------|-------------------|----------|
| `fg_color`             | `[hex, hex]`      | Main foreground / background tint for frames |
| `text_color`           | `[hex, hex]`      | Primary text colour and disabled/secondary text |
| `button_color`         | `[hex, hex]`      | Default button fill |
| `button_hover_color`   | `[hex, hex]`      | Button fill on hover |
| `border_color`         | `[hex, hex]`      | Input / frame border |
| `text_muted`           | `hex`             | Muted / placeholder text |
| `status_success`       | `hex`             | Success indicators |
| `status_error`         | `hex`             | Error indicators |
| `button_success`       | `[hex, hex]`      | Success-action button fill |
| `button_success_hover` | `[hex, hex]`      | Success-action button hover |
| `accent`               | `hex`             | Accent highlights |
| `surface`              | `hex`             | Card / panel surface |
| `surface_elevated`     | `hex`             | Elevated surface (tooltips, popovers) |
| `overlay_bg`           | `hex`             | Overlay / modal background |
| `card_border`          | `hex`             | Card / panel border |
| `select_bg`            | `hex`             | Selection highlight background |
| `text_on_surface`      | `hex`             | Text on top of surface elements |

### Minimal example

```json
{
  "name": "sakura",
  "emoji": "🌸",
  "light": {
    "fg_color": ["#FFF0F5", "#FFFFFF"],
    "text_color": ["#1A1A1A", "#666666"],
    "button_color": ["#FF69B4", "#DB4F91"],
    "button_hover_color": ["#DB4F91", "#B8396F"],
    "border_color": ["#FF69B4", "#DB4F91"],
    "text_muted": "#999999",
    "status_success": "#28a745",
    "status_error": "#dc3545",
    "button_success": ["#28a745", "#1E7E34"],
    "button_success_hover": ["#218838", "#155724"],
    "accent": "#FF69B4",
    "surface": "#FFFFFF",
    "surface_elevated": "#FFF5F9",
    "overlay_bg": "#FFF0F5",
    "card_border": "#CCCCCC",
    "select_bg": "#FF69B4",
    "text_on_surface": "#1A1A1A"
  },
  "dark": {
    "fg_color": ["#2A1520", "#3A1E2E"],
    "text_color": ["#FFFFFF", "#CCCCCC"],
    "button_color": ["#FF69B4", "#DB4F91"],
    "button_hover_color": ["#DB4F91", "#B8396F"],
    "border_color": ["#FF69B4", "#DB4F91"],
    "text_muted": "#888888",
    "status_success": "#28a745",
    "status_error": "#dc3545",
    "button_success": ["#28a745", "#1E7E34"],
    "button_success_hover": ["#218838", "#155724"],
    "accent": "#FF69B4",
    "surface": "#2b2b2b",
    "surface_elevated": "#2b2b2b",
    "overlay_bg": "#1a1a1a",
    "card_border": "#4a4a4a",
    "select_bg": "#8B3A60",
    "text_on_surface": "#FFFFFF"
  }
}
```

## Theme directories

Themes are loaded from two directories, in order:

| Priority | Directory | Purpose |
|----------|-----------|---------|
| 1 (base) | `themes/` at the project root | Bundled themes shipped with the app |
| 2 (override) | `~/.media_downloader/themes/` | User themes — override bundled themes on name collision |

If you create `~/.media_downloader/themes/blue.json`, it replaces the
bundled blue theme.

## Bundled themes

The app ships with 18 themes:

| Emoji | Name    | Accent colour |
|-------|---------|---------------|
| 🟡    | amber   | `#F59E0B`     |
| 🔵    | blue    | `#007BFF`     |
| 🪸    | coral   | `#FF6B6B`     |
| 💫    | cyan    | `#06B6D4`     |
| 💚    | emerald | `#10B981`     |
| 👑    | gold    | `#D4A017`     |
| 🟢    | green   | `#22C55E`     |
| 💙    | indigo  | `#6366F1`     |
| 🍈    | lime    | `#84CC16`     |
| ⚓    | navy    | `#1E3A5F`     |
| 🟠    | orange  | `#FF8C00`     |
| 🌸    | pink    | `#EC4899`     |
| 🟣    | purple  | `#9333EA`     |
| 🔴    | red     | `#EF4444`     |
| 🌹    | rose    | `#F43F5E`     |
| ⚫    | slate   | `#64748B`     |
| 🔷    | teal    | `#14B8A6`     |
| 💜    | violet  | `#8B5CF6`     |

## Theme persistence

When the user selects a theme, it is saved to the config file
(`~/.media_downloader/config.json` by default) under `ui.theme.color_theme`.
On next launch the saved theme is restored automatically.

## Architecture notes

- Theme JSON files contain the raw colour palette only. The CTK widget
  structure (`CTkButton`, `CTkEntry`, etc.) is built at runtime by
  `ThemeConfig.get_theme_json()` in `src/core/config.py`.
- The theme loader lives in `src/core/themes/__init__.py` and caches results
  after first load. Call `reload_themes()` to force a re-scan.
- The dropdown in the UI is built dynamically from discovered themes — there
  is no hardcoded list of theme names.
