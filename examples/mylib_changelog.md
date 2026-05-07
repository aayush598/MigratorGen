# Changelog

## 4.0.0 - 2024-09-01

### Breaking Changes

- Renamed `Database` class to `DatabaseClient`
- `execute_query()` has been renamed to `query()`
- Removed the `legacy_mode` argument from `connect()` - this parameter no longer has any effect
- Moved `ConnectionPool` from `mylib.pool` to `mylib.connections`
- The `parse_result()` function now returns a `ResultSet` object instead of a plain dict; use `.to_dict()` if you need the old behavior

### Deprecations

- `batch_execute()` is deprecated; use `query_many()` instead

---

## 4.1.0 - 2024-10-15

### Breaking Changes

- Renamed `ResultSet.rows` attribute to `ResultSet.records`
- Added required `schema` argument to `DatabaseClient.__init__()`