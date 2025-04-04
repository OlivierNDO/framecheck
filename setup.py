from setuptools import setup, find_packages

setup(
    name="valipy",
    version="0.1.0",
    packages=find_packages(),
    install_requires=["pandas", "jinja2"],
    author="Your Name",
    author_email="your.email@example.com",
    description="Easy data validation for pandas DataFrames",
    url="https://github.com/yourusername/valipy",
)
