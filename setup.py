from setuptools import setup, find_namespace_packages

setup(
    name="cli-ghl-pool-profits",
    version="1.0.0",
    description="GoHighLevel CLI + agency-wide audit tooling for Pool Profits",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    package_data={"cli_anything.gohighlevel": ["skills/*.md"]},
    install_requires=[
        "click>=8.0.0",
        "prompt-toolkit>=3.0.0",
        "requests>=2.28.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-anything-gohighlevel=cli_anything.gohighlevel.gohighlevel_cli:main",
            "ghl=cli_anything.gohighlevel.gohighlevel_cli:main",
        ],
    },
    python_requires=">=3.10",
)
