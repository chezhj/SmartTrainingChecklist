# SimFlow Rebrand Instructions
## For Claude in VS Code (Claude Code)

This document tells Claude exactly what to rename, replace, and update
to rebrand the project from `fly.vdwaal.net` / `SmartTrainingChecklist`
to **SimFlow**.

---

## 1. Django App & Project Names

### Settings (`settings.py` or `config/settings/*.py`)
- Replace `SITE_NAME = "..."` or any string with the old name → `"SimFlow"`
- Update `ALLOWED_HOSTS` if it contains hardcoded `fly.vdwaal.net` references
  - Keep the domain itself — just remove it from display strings
- Update `DEFAULT_FROM_EMAIL` display name if it contains the old name

### App labels (`apps.py`)
- Any `verbose_name` that reads `"Smart Training Checklist"` or similar → `"SimFlow"`

---

## 2. Plugin Identifier

### Current (do NOT change — user bindings will break post-release)
```
fly.vdwaal.net/check_next_item
```

### Before first public release, rename to:
```
simflow/check_next_item
```
> ⚠️  Only safe to rename BEFORE any public release.
> After release, treat this string as permanent.

### config.ini / plugin config file
- Replace any reference to `fly.vdwaal.net` in the plugin config with `simflow`
- Plugin folder name: rename `fly_vdwaal` or similar → `simflow`
- Plugin display name in `PI_simflow.py` header comment → `SimFlow`

---

## 3. Templates

### Base template (`base.html` or `_base.html`)
- `<title>` tag: replace old name → `SimFlow`
- `<meta name="application-name">` → `SimFlow`
- `<meta name="description">` → `"SimFlow — X-Plane procedure companion. Stay in the flow."`
- Any footer copyright string → `SimFlow`
- Header/navbar brand text → `SimFlow`
- Replace old logo `<img>` or inline SVG with new SimFlow mark (files provided)

### favicon
- Replace existing favicon with `favicon.ico` from this package
- Add to `<head>`:
```html
<link rel="icon" type="image/x-icon" href="{% static 'checklist/img/favicon.ico' %}">
<link rel="icon" type="image/png" sizes="32x32" href="{% static 'checklist/img/simflow-icon-32.png' %}">
<link rel="icon" type="image/png" sizes="16x16" href="{% static 'checklist/img/simflow-icon-16.png' %}">
<link rel="apple-touch-icon" sizes="128x128" href="{% static 'checklist/img/simflow-icon-128.png' %}">
```

### All other templates
Search for and replace these strings across all `.html` files:
| Find | Replace with |
|------|-------------|
| `fly.vdwaal.net` (display text only) | `SimFlow` |
| `Smart Training Checklist` | `SimFlow` |
| `SmartTrainingChecklist` | `SimFlow` |
| `simulation only` | `X-Plane · Zibo 737` |
| `Made by: ChezHJ` | keep as-is (credit) |

> ⚠️  Do NOT replace `fly.vdwaal.net` in URLs, ALLOWED_HOSTS, or href attributes.
> Only replace it where it appears as visible display text.

---

## 4. Static Files

Copy the following files into your project at this exact path:

```
C:\Users\h\Code\SmartTrainingChecklist\checklist\static\checklist\img\
```

Create the `img\` folder if it doesn't exist yet:
```powershell
New-Item -ItemType Directory -Path checklist\static\checklist\img
```

Then copy:

```
favicon.ico
simflow-icon-16.png
simflow-icon-32.png
simflow-icon-48.png
simflow-icon-64.png
simflow-icon-128.png
simflow-icon-256.png
simflow-icon-512.png
simflow-icon-green-64.png
simflow-icon-green-256.png
simflow-mark.svg
simflow-wordmark.svg
simflow-header.svg
```

In **development** (`DEBUG=True`) Django serves these automatically — nothing else needed.

For **production** deployments only, run:
```bash
python manage.py collectstatic
```

---

## 5. Python Files

### XPython3 plugin file
- Filename: rename to `PI_simflow.py`
- Header docstring: update name → `SimFlow`
- Any string `"fly.vdwaal.net"` used as a display label → `"SimFlow"`
- API endpoint URLs: keep `fly.vdwaal.net` domain — this is infrastructure, not branding

### Django models / admin
- Any `verbose_name_plural` with old name → update
- Admin site header (`admin.site.site_header`) → `"SimFlow Admin"`
- Admin site title (`admin.site.site_title`) → `"SimFlow"`

---

## 6. Documentation & README

- `README.md` title and references → SimFlow
- Any `SPEC.md`, `MODEL_DESIGN.md`, `PHASE_3_ALPHA_SPEC.md` headers → add SimFlow branding
- `PI_SimBrief2Zibo.py` → this file should be DELETED before v2.0 ships (already noted)

---

## 7. Git / Repo

After completing the above:
```bash
git add -A
git commit -m "rebrand: fly.vdwaal.net → SimFlow"
```

The GitHub repo name (`SmartTrainingChecklist`) can stay as-is or be renamed
to `simflow` via GitHub Settings → Repository name.

---

## What NOT to change

| Item | Reason |
|------|--------|
| `fly.vdwaal.net` domain in URLs/config | Infrastructure — domain stays |
| `fly.vdwaal.net/check_next_item` command | User bindings break on rename (pre-release only — see section 2) |
| `dataref_expression` / `show_expression` fields | Do not modify — xChecklist export depends on these |
| `PI_SimBrief2Zibo.py` content | Delete the file entirely, don't edit |
| Database migrations | No model renames required |

---

## Brand Reference

| Token | Value |
|-------|-------|
| Product name | SimFlow |
| Plugin identifier | `simflow` |
| Domain | `fly.vdwaal.net` (unchanged) |
| Primary dark | `#0D1512` |
| Primary green | `#0F6B54` |
| Mid green | `#1A8A6C` |
| Accent mint | `#22C9A0` |
| Light background | `#F4F5F3` |
| Tagline | *Stay in the flow.* |

