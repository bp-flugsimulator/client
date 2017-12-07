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

    install_reqs = parse_requirements(file, session="r")
    install_reqs_list = [str(ir.req) for ir in install_reqs]
    return install_reqs


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
    py_modules=["client"],
    packages=find_packages(
        exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
)
