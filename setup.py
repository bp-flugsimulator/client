"""
Setup file for client executable.
"""
from setuptools import setup, find_packages
from pip.req import parse_requirements


def get_requirements(file):
    """
    Reads the requirements.txt and parses the needed
    dependencies and returns them as an array.

    Returns
    -------
        An array of dependencies.
    """

    return parse_requirements(file, session="r")


setup(
    name="bp-flugsimulator-client",
    description="Client for the bp-flugsimulator",
    version="1.0",
    scripts=[],
    url="https://github.com/bp-flugsimulator/client",
    author="bp-flugsimulator",
    license="MIT",
    install_requires=get_requirements("requirements.txt"),
    python_requires=">=3.4",
    packages=find_packages(exclude=[
        "*.tests",
        "*.tests.*",
        "tests.*",
        "tests",
    ]),
    entry_points={
        'console_scripts': ['bp-flugsimulator-client=client.__main__:main']
    },
    test_suite="tests",
)
