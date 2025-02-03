from setuptools import setup, find_packages

setup(
    name="cryptobot",
    version="1.0.0",
    description="A professional Solana trading bot with Streamlit dashboard",
    author="Etherlyweiner",
    author_email="etherlyweiner@example.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        line.strip()
        for line in open("requirements.txt")
        if line.strip() and not line.startswith("#")
    ],
    python_requires=">=3.10,<3.11",
    entry_points={
        "console_scripts": [
            "cryptobot=cryptobot.app:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.10",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
    include_package_data=True,
    package_data={
        "cryptobot": ["config/*.json", "assets/*"],
    },
)
