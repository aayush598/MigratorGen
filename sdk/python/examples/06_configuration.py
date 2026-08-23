"""
SDKConfig — layered configuration: defaults → env vars → config file → kwargs.
"""

from migrator_gen import SDKConfig

# 1. Defaults
cfg = SDKConfig()
print(f"Default base_url: {cfg.base_url}")
print(f"Default timeout: {cfg.timeout}s")
print(f"Default mode: {cfg.mode}")

# 2. Programmatic overrides
cfg = SDKConfig.build(
    mode="local",
    base_url="",
    timeout=60,
    max_retries=5,
    log_level="DEBUG",
)
print(f"\nOverridden timeout: {cfg.timeout}")
print(f"Local defaults: {SDKConfig.local_defaults()}")

# 3. Serialisation
d = cfg.to_dict()
print(f"\nConfig dict keys: {list(d.keys())}")

env = cfg.to_env()
print(f"Env var for timeout: MIGRATOR_TIMEOUT={env.get('MIGRATOR_TIMEOUT')}")

# 4. From a TOML config file (uncomment and create the file):
# cfg = SDKConfig.build(config_path=Path.home() / ".migrator-gen.toml")
#
# Contents of ~/.migrator-gen.toml:
# [migrator_gen]
# mode = "local"
# timeout = 60
# log_level = "DEBUG"
