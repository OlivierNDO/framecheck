from setuptools import setup, find_packages

setup(
    name="framecheck",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pandas"
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
            "pytest-html"
        ]
    },
    author="Nick Olivier",
    author_email="Olivier_N@alum.lynchburg.edu",
    description="Lightweight, flexible, and intuitive validation for pandas DataFrames.",
    url="https://github.com/OlivierNDO/framecheck/",
)
