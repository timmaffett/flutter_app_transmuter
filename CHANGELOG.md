# Changelog for flutter_app_transmuter

## 2.1.1

* Changed `brand_source_directory` property to use POSIX paths, regardless of platform, to ensure
  uniformity of paths between ios and windows.
* Clean up old test/development code and experiments.

## 2.1.0

* **YAML-driven transmute operations** — All transmute operations are now defined in YAML
  (`default_transmute_operations.dart`) and can be overridden or extended via a
  `transmute_operations.yaml` file in the target project.
* **Brand management workflow** — Added `master_transmute.yaml` file mapping system with
  `--copy`, `--diff`, `--update`, and `--switch` commands for managing multiple branded
  app variants.
* **Brand switching** — `--switch <new_brand_dir>` updates the current brand files from the
  project, copies new brand files in, and runs post-switch operations (clean, pub get,
  flutterfire configure, build, etc.).
* **Post-switch operations pipeline** — Configurable post-switch steps in YAML with
  platform filtering, flag gating (`+flutterfire`, `+build`), and step exclusion (`-stepname`).
* **`--executepostprocess`** — Run post-switch operations independently without switching brands.
* **`--showdefaultyaml` / `--writedefaultyaml`** — View or export the built-in default
  transmute operations YAML for customization.
* **`--check` / `--verify`** — Check that project files match transmute.json values,
  with `--verify` offering interactive fixes.
* **`--status`** — Show current brand info with file diffs and transmute value checks.
* **Auto-answer CLI flags** — `--yes`, `--skip`, `--brandfile`, `--projectfile`,
  `--transmutevalue`, `--filevalue`, and `--fatal-prompts` for non-interactive CI/CD automation.
* **Rainbow brand banner** — Displays the `brand_name` from transmute.json in a colorful
  HSL-cycling banner on startup.
* **`brand_source_directory`** — Automatically tracked in transmute.json when using `--copy`,
  enabling directory-free `--diff`, `--update`, and `--executepostprocess` commands.
* **Brand directory consistency check** — Warns when a command-line brand directory doesn't
  match the stored `brand_source_directory`.
* **Pubspec version sync** — `--update` checks if `pubspec.yaml` version is newer than
  `transmute.json` `pubspec_version` and offers to update.
* **Cross-platform path normalization** — `brand_source_directory` is always stored with
  POSIX (forward-slash) paths and converted to native format when read, preventing spurious
  diffs when building on different operating systems.
* **Unit tests** — Added comprehensive test suites for transmute operations, file utilities,
  and brand file operations.
* **CI/CD** — GitHub Actions workflow creates a real Flutter project, runs the transmuter,
  and verifies file updates.
* Removed obsolete example project.
* Updated dependencies (`args`, `chalkdart`, `glob`, `path`, `yaml`, `yaml_writer`).
* Added `test` dev dependency.

## 2.0.0

* Essentially a complete re-write of the code to better architecture and robust feature set
  required for to make this a more capable and powerful tool for branding.

## 1.0.0

* Fork from my branch of [flutter_app_rebrand 1.0.3](https://github.com/sarj33t/flutter_app_rebrand/pull/29)
* Remove all code that was originally from flutter_launcher_icons — we will use that package
  directly and not try to reproduce any of its functionality.
