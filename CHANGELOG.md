# Changelog for flutter_app_transmuter

## 2.2.1

* provision: missing Google Application Default Credentials now exits with a full setup
  walkthrough (install gcloud via winget/brew/link, open a NEW terminal, run
  `gcloud auth application-default login` as the configured admin account, or pass
  --creds) instead of a raw DefaultCredentialsError traceback.
* provision: check-agreements generates a ready-to-send email to each blocked team's
  Apple Account Holder (accept the updated Developer Program License Agreement, with
  the team's developer.apple.com deep link), saves it into the brand dir, and prints a
  mailto: link that opens the user's mail program with to/subject/body prefilled. The
  ASC API access-request email flow gains the same mailto: link. Optional template
  override: apple.agreements_email_template in transmute_provisioning.yaml.
* provision: a missing/placeholder firebaseProjectNumber is now a fixable audit issue
  (recorded from google-services.json); mismatches are flagged for manual resolution.
* All organization-specific internal names removed from shipped sources (internal
  config key netparkAdminGrantee -> adminGrantee; yaml key was already admin_grantee).

## 2.2.0

* New `transmute provision <verb>` command family: brand cloud provisioning and auditing
  (Google Cloud / Firebase / Play / App Store Connect) driven by a bundled Python engine.
  Verbs: `init`, `audit`, `audit-unique`, `create-project`, `create-apps`, `create-keys`,
  `create`, `create-apple`, `add-asc-key`, `check-agreements`, `check-personal-ios-dev-certs`.
* Configured per-project by a new `transmute_provisioning.yaml` (written by
  `transmute provision init`): required Google APIs, API key purposes with restrictions and
  display-name templates ({customerIds} substitution), signing-cert fingerprints, billing,
  Apple capabilities, APNs backup dir, and optional server-copy notices with per-customer URLs.
* Requires Python 3.10+ plus a few pip packages for the provision verbs only; the driver
  detects Python (including the broken Windows Store alias) and prints the exact
  `pip install` command when packages are missing. Everything else works without Python.

## 2.1.7

* Fix `--dryrun` not being honored by `git_restore` operations: `--transmute --dryrun` actually ran
  `git restore` and overwrote the working file. Dry run now prints what would be restored instead.
* Brand/project file conflict prompts now offer (Q) quit, which stops the tool immediately.
  During `--switch` the prompt is (B/P/Q) with **no N/skip option** — a "skipped" file would be
  silently overwritten by step 2's brand copy, so the choices are take brand (B), keep project (P),
  or abort the switch (Q, the default). Plain `--update` keeps N (skip is honest there) and adds Q.
* Add `--check_pubdev` command: queries pub.dev for the latest published version and prints the
  update command if a newer one is available.
* Regular commands now check pub.dev for updates automatically in the background (at most once
  every 24 hours, cached; silent and zero-delay when offline) and print a notice after the run
  when a newer version is available.
* Document updating the tool (re-running `dart pub global activate` is the update) in `--help`
  output and the README installation section.
* README: document that multi-line operation regexes must use `\s*` or `\r?\n` instead of a bare
  `\n` (on Windows, `git restore` writes CRLF, silently breaking hardcoded-`\n` patterns).

## 2.1.6

* Add `value_is_flag` operation field: marks an operation's `json_key` as an enable-flag rather than
  a substitution value. Auto-detected when `replacement` contains no `$value`. Flag-gated operations
  are disabled by a missing key or a `false`/`no`/`0`/`off` value, and `--check`/`--verify` treat
  "pattern no longer matches" as applied (MATCH).
* Fix `--verify`: never offer to adopt the regex match from a file as the value of a flag-gated
  operation's `json_key` (previously a missing flag key could get raw file content — e.g. an entire
  Info.plist XML block — written into `transmute.json`, silently re-enabling the operation for
  brands that had it deliberately unset). On a flag-op mismatch, only (T) apply / (N) skip are
  offered; `--filevalue` skips with a note instead of corrupting `transmute.json`.

## 2.1.5

* Normalize use of space (instead of optional '=') in README docs for command lines

## 2.1.4

* Document global activation (`dart pub global activate flutter_app_transmuter`) at the top of the
  README as the recommended install, and use the `transmute` executable in all README examples
  (instead of `dart run flutter_app_transmuter:main`).

## 2.1.3

* Add `--tagrelease <brand_dir>` command to record a branded release as an annotated git tag
  (cross-platform replacement for shell tagging scripts — no `bash`/`jq`/`sed`/`date` required).
* `--tagrelease` options: `--platform`, repeatable `--note`, `--push`, `--force`; honors `--dryrun`
  (preview) and `--fatal-prompts` (CI). Refuses on a dirty working tree or an existing tag.
* Configurable via an optional `tag_release:` block in `master_transmute.yaml` (tag-name template,
  slug strip pattern, required files, platform defaults, and metadata sources: `value`, `json_key`,
  `file`+`yaml_key`, `command`). Shipped defaults produce `release/{slug}/{platform}/{version}`.
* Platform resolution order: `--platform` → `default_platform_by_os` (host-OS-keyed) `default_platform` → interactive prompt.
* Add `--version` flag and `Constants.packageVersion`, with a drift-guard test ensuring it stays in sync with `pubspec.yaml`.
* Document `--tagrelease` and the `tag_release:` config in README and AGENTS docs; add a `tag_release:` example to the example project.
* Add "Reproducing a tagged build later" and "Inspecting release tags" sections to the `--tagrelease` documentation.
* Improve README.md
* Add `git_restore` transmute operation type to restore files to git `HEAD` baseline.
* Execute `git_restore` operations in a dedicated first pass before all value-driven operations.
* Document `git_restore`, `always_run`, and operation execution order in README and AGENTS docs.

## 2.1.2

* Add example app with 3 brands and documentation.
* Add AGENTS.md file
* Improve README.md

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
