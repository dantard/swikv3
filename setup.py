from setuptools import setup, find_packages

setup(
    name="swik",
    version="0.0.3",
    packages=find_packages(where="src"),  # Specify src directory
    package_dir={"": "src"},  # Tell setuptools that packages are under src
    install_requires=[
        "pyqt5",
        "pymupdf >= 1.18.17",
        "easyconfig",
        "pyhanko",
        "psutil",
        "pyHanko[image-support]",
        "easyconfig@git+https://github.com/dantard/easyconfig.git@revolution",
        "pycairo",
        "fonttools",
        "glib",
        "pyopenssl"
    ],
    author="Danilo Tardioli",
    author_email="dantard@unizar.es",
    description="A PDF Swiss Knife",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/dantard/swikv3",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.10',
    entry_points={
        'console_scripts': [
            'swik=swik.swikv3:main',
        ],
    },
    package_data={
        "swik": ["fonts/*"],
    },
    include_package_data=True,

    data_files=[
        ("share/applications", ['desktop/swik.desktop']),  # Copy to a specific location
    ],
)
