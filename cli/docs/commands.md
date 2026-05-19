# Commands

## `create`
Create a migrator package from a changelog file.

```
migrator-gen create --changelog path/to/changelog.json --library mylib --output ./out
```

## `update`
Update an existing migrator with a new changelog.

```
migrator-gen update --existing rules.json --new-changelog changelog.json
```

## `migrate` / `run`
Apply migrations to a file or directory.

```
migrator-gen migrate src/ --rules rules.json --dry-run
migrator-gen run app.py --rules rules.json
```

## `preview`
Preview migration changes as a unified diff.

```
migrator-gen preview app.py --rules rules.json
```

## `rules`
List all rules from a rules file.

```
migrator-gen rules --rules rules.json --json
```

## `interactive`
Guided rule builder — prompts for each field.

```
migrator-gen interactive --output my_rules.json
```

## `export-schema`
Export the JSON Schema for `MigrationFile`.

```
migrator-gen export-schema --output schema.json
```

## `validate-rules`
Validate a rules file for correctness.

```
migrator-gen validate-rules rules.json
```

## `diff-rules`
Show added, removed, and modified rules between two files.

```
migrator-gen diff-rules --old v1.json --new v2.json
```

## `audit`
Scan a project for version references matching rules.

```
migrator-gen audit project/ --rules rules.json
```

## `auto-upgrade`
Detect dependencies from `requirements.txt`, `pyproject.toml`, or source imports.

```
migrator-gen auto-upgrade project/
```
