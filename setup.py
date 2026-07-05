from setuptools import setup, find_packages
from pathlib import Path

here = Path(__file__).parent.resolve()

long_description = (here / "README.md").read_text(encoding="utf-8")

setup(
    name="openrouter-checker",
    version="1.0.0",
    description="OpenRouter AI Model Checker and Interactive Chat Manager",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/clashssd/openrouter-checker",
    author="CLASHSSD",
    author_email="contact@openrouter.ai",
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.14",
        "Operating System :: OS Independent",
        "Topic :: Utilities",
    ],
    keywords="openrouter ai chat api rate-limit fallback streaming",
    project_urls={
        "Bug Reports": "https://github.com/clashssd/openrouter-checker/issues",
        "Source": "https://github.com/clashssd/openrouter-checker",
        "Documentation": "https://github.com/clashssd/openrouter-checker#readme",
    },
    packages=find_packages(include=["ai", "ai.core", "ai.core.setting_models"]),
    package_dir={"": "."},
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0.0",
        "typing-extensions>=4.5.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "pylint>=2.17.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "openrouter-checker=ai.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
