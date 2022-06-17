from setuptools import setup, find_packages

setup(
    name="geodata-mart",
    version="0.0.1",
    packages=find_packages(include=[".*"]),
    install_requires=[],
    extras_require={"dev": ["black", "python-dotenv", "pytest", "mypy"]},
    python_requires="~=3.10",
)
