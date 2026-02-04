from setuptools import setup, find_packages

setup(
    name="ai-perp-dex",
    version="0.1.0",
    description="AI Agent SDK for trading perpetual futures",
    author="AI Perp DEX Team",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "httpx>=0.25",
        "solders>=0.21",
        "solana>=0.32",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
