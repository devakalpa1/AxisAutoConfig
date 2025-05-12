#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="axis_config_tool",
    version="1.0.0",
    author="Geoffrey Stephens",
    author_email="gstephens@storypolish.com",
    description="AxisAutoConfig: Tool for Axis Camera Setup & Configuration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/devakalpa1/AxisAutoConfig",
    project_urls={
        "Bug Tracker": "https://github.com/devakalpa1/AxisAutoConfig/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Development Status :: 5 - Production/Stable",
        "Environment :: X11 Applications :: Qt",
        "Topic :: Multimedia :: Video",
        "Topic :: System :: Networking",
    ],
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "axis_config_tool": ["resources/*"],
    },
    python_requires=">=3.6",
    install_requires=[
        "PySide6>=6.0.0",
        "psutil>=5.8.0",
        "requests>=2.25.0",
        "zeep>=4.0.0",
    ],
    entry_points={
        "console_scripts": [
            "axis-config-tool=axis_config_tool.run:main",
        ],
    },
)
