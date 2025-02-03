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
        "streamlit>=1.26.0,<2.0.0",
        "solana>=0.30.0,<0.37.0",
        "anchorpy>=0.14.0,<0.21.0",
        "solders>=0.15.0,<0.26.0",
        "aiohttp>=3.8.0,<4.0.0",
        "python-dotenv>=0.19.0",
        "cryptography>=42.0.0,<43.0.0",
        "prometheus-client>=0.16.0",
        "aiofiles>=23.1.0,<24.0.0",
        "nest-asyncio>=1.5.7,<2.0.0",
        "asyncio>=3.4.3,<4.0.0",
        "redis>=5.0.0,<6.0.0",
        "aioredis>=2.0.0,<3.0.0",
        "requests>=2.28.0,<3.0.0",
        "websockets>=10.3,<11.0",
        "pandas>=2.2.0,<3.0.0",
        "numpy>=1.26.0,<2.0.0",
        "ta>=0.10.0,<0.11.0",
        "fastapi>=0.109.0,<0.110.0",
        "uvicorn>=0.27.0,<0.28.0",
        "psutil>=5.9.0,<6.0.0",
        "pywin32>=308",
        "python-json-logger>=2.0.7",
        "plotly>=5.16.0,<6.0.0",
        "black>=24.1.0,<25.0.0",
        "isort>=5.12.0,<6.0.0",
        "flake8>=6.1.0,<7.0.0",
        "python-jose[cryptography]>=3.3.0,<4.0.0",
        "passlib>=1.7.4,<2.0.0",
        "bcrypt>=4.1.2,<5.0.0",
        "structlog>=24.1.0,<25.0.0"
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
