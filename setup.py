#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="serverdeck-cli",
    version="1.0.0",
    description="Linux server monitoring dashboard and management tool",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="ServerDeck Team",
    author_email="kontakt.pan.n@gmail.com",
    url="https://github.com/Norbertkkl/ServerDeck",
    license="MIT",
    packages=find_packages(include=["serverdeck", "serverdeck.*"]),
    include_package_data=True,
    package_data={
        "serverdeck": [
            "locales/*.yaml",
            "locales/*.yml",
            "templates/*.yaml",
            "templates/*.yml",
            "templates/*.service"
        ]
    },
    install_requires=[
        "pyyaml>=6.0.1",
        "psutil>=5.9.0",
        "discord.py>=2.3.0"
    ],
    entry_points={
        "console_scripts": [
            "serverdeck-cli=serverdeck.cli:main",
            "serverdeck=serverdeck.cli:main",
            "serverdeck-bot=serverdeck.bot.main:main"
        ]
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Monitoring",
        "Topic :: System :: Systems Administration",
        "Topic :: Communications :: Chat"
    ],
    python_requires=">=3.9"
)

