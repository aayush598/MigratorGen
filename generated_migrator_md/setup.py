from setuptools import setup, find_packages

setup(
    name="mylib_migrator",
    version="1.0.0",
    description="Auto-generated code migrator for mylib",
    packages=find_packages(),
    install_requires=["libcst>=1.0.0"],
    entry_points={
        "console_scripts": [
            "mylib_migrator=mylib_migrator.__main__:main",
        ],
    },
    python_requires=">=3.8",
)
