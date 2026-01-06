from setuptools import setup, find_packages

setup(
    name="myson-tools",
    version="0.1.4",
    description="A set of bioinformatics tools (by Myson)",
    author="Myson Dio",
    license='GPL-3.0',
    url="https://github.com/gtRZync/myson-tools",
    packages=find_packages(),
    install_requires=[
        "pandas",
        "openpyxl",
        "rich",
        "python-dotenv",
        "odfpy",
        "scikit-bio",
    ],
    entry_points={
        "console_scripts": [
            "myson-tools = myson_tools.cli:main"
        ]
    },
    include_package_data=True,
    python_requires=">=3.8",
)