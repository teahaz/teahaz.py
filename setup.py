from setuptools import setup, find_packages
from teahaz import __version__

setup(
    name="teahaz.py",
    version=__version__,
    packages=["teahaz"],
    license="MIT",
    description="The official Python API wrapper for the Teaház protocol.",
    long_description="Not yet available.",
    install_requires=["requests", "cryptography"],
    url="https://github.com/bczsalba/teahaz.py",
    author="BcZsalba",
    author_email="bczsalba@gmail.com",
)
