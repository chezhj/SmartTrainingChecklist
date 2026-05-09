# xFlow Plugin Changelog

All notable changes to the xFlow X-Plane plugin are documented here.
Plugin versions are independent from the web app version.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [1.0.0] — 2026-05-09

### Added
- `PLUGIN_VERSION` constant — plugin now identifies itself to the server via
  `X-Plugin-Version` request header on all API calls.
- Version compatibility handshake: server responds with `plugin_status`
  (`ok` | `warn` | `blocked`). Plugin logs a warning or stops polling
  accordingly.
- SOP metadata logging on connect: `[xFlow] connected — B738 SOP v1.0.0 | plugin v1.0.0`.
- `_blocked` flag — when server rejects the plugin version the flight loop
  halts cleanly without flooding the server with retries.

### Fixed
- Install instructions in the module docstring were incorrect (said to copy
  the `xFlow/` folder; `PI_xFlow.py` must be placed directly in `PythonPlugins/`).
