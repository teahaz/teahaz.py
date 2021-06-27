from setuptools import setup, find_packages

setup(
    name="teahaz.py",
    version="0.0.4",
    packages=["teahaz"],
    license="MIT",
    description="The official API wrapper for the teahaz server",
    long_description="TBA",
    install_requires=["requests", "cryptography"],
    url="https://github.com/bczsalba/teahaz.py",
    author="BcZsalba",
    author_email="bczsalba@gmail.com",
)
