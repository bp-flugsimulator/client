"""
Setup file for client executable.
"""
from setuptools import setup, find_packages
from pip.req import parse_requirements
from platform import system


def get_requirements():
    """
    Reads the requirement file and parses the needed
    dependencies and returns them as an array.

    Returns
    -------
        An array of dependencies.
    """
    if system() == "Windows":
        file = "win_requirements.txt"
    elif system() == "Linux":
        file = "linux_requirements.txt"

    install_reqs = parse_requirements(file, session="r")
    install_reqs_list = [str(ir.req) for ir in install_reqs]
    return filter(lambda x: x is not None, install_reqs_list)


setup(
    name="bp-flugsimulator-client",
    description="Client for the bp-flugsimulator",
    version="1.0",
    scripts=[],
    url="https://github.com/bp-flugsimulator/client",
    author="bp-flugsimulator",
    license="MIT",
    install_requires=get_requirements(),
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
