# Application data paths

DocuWizard stores all user content and settings under OS-standard per-user directories
(via [`platformdirs`](https://pypi.org/project/platformdirs/)).

| Purpose | Helper | Typical location |
|---------|--------|------------------|
| Projects, SQLite DB, copied files | `paths.data_dir()` | Windows: `%LOCALAPPDATA%\DocuWizard\DocuWizard` · macOS: `~/Library/Application Support/DocuWizard` · Linux: `~/.local/share/DocuWizard` |
| Settings JSON | `paths.config_dir()` | Windows: `%APPDATA%\DocuWizard\DocuWizard` · macOS: `~/Library/Preferences/DocuWizard` · Linux: `~/.config/DocuWizard` |
| Project file copies | `paths.projects_dir()` | `{data_dir}/projects/<project_id>/files/` |
| Database | `paths.db_path()` | `{data_dir}/docuwizard.db` |
| Settings file | `paths.config_path()` | `{config_dir}/settings.json` |

Call `paths.ensure_app_dirs()` at startup to create missing directories.

API keys must never be committed; they belong in encrypted/OS keychain storage (issue #30), not in this repo.
