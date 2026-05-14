# Modular Licensing

VelaFlow prepares for feature-based licensing without implementing payment,
auth, server activation, or online checks yet.

## LicenseService

File: `core/licensing.py`

All module access should go through `LicenseService`:

```python
license_service.module_enabled("render")
license_service.is_enabled("batch_render_enabled")
```

Avoid scattering checks like `if premium` around the codebase.

## Local Config

File: `config/license.json`

The current config is a local mock license. It is meant for development and UI
gating only.

Example:

```json
{
  "package": "Studio",
  "expires_at": "2027-05-09",
  "feature_flags": {
    "render_enabled": true,
    "export_without_watermark": true
  }
}
```

## Feature Flags

File: `core/feature_flags.py`

Supported flags:

- `core_enabled`
- `director_enabled`
- `motion_enabled`
- `render_enabled`
- `clips_enabled`
- `canvas_enabled`
- `marketing_enabled`
- `assets_enabled`
- `providers_enabled`
- `licensing_enabled`
- `batch_render_enabled`
- `export_without_watermark`
- `commercial_use`

## Sidebar Status

The app sidebar displays package, expiry, build version, active render profile,
theme, watermark state, and key module flags. This is display-only in V7.8.

## Future Packages

Free:

- Core
- Basic project
- Watermark

Creator:

- Core
- Director
- Motion
- Canvas
- Basic export

Studio:

- Core
- Director
- Motion
- Render
- Clips
- Canvas
- Marketing
- Batch export
- No watermark

Enterprise:

- Full access
- API ready
- Team ready
- Cloud ready

## Not Implemented Yet

- Online activation
- Payment
- User auth
- License server
- Team accounts
- Cloud sync
