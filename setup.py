from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
LONG_DESCRIPTION = (here / "README.md").read_text(encoding="utf-8")

VERSION = "0.1.19"

# Setting up
setup(
    name="pyeconet",
    version=VERSION,
    author="William Scanlon",
    description="Interface to the unofficial EcoNet API",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    package_dir={"": "src"},
    packages=find_packages(
        where="src", exclude=["dist", "*.test", "*.test.*", "test.*", "test"]
    ),
    install_requires=["aiohttp>=3.6.0", "paho-mqtt>=1.5.0"],
    keywords=["econet", "rheem", "api"],
    python_requires=">=3.9, <4",
    url="https://github.com/w1ll1am23/pyeconet",
    project_urls={
        "Bug Reports": "https://github.com/w1ll1am23/pyeconet/issues",
        "Source": "https://github.com/w1ll1am23/pyeconet",
    },
)
