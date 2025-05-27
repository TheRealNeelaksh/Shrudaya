from setuptools import setup, find_packages

# Read dependencies from requirements.txt
with open("requirements.txt") as f:
    required_packages = f.read().splitlines()

setup(
    name="Shrudaya",
    version="1.0.0",
    description="Shrudaya: A fully voice-based AI assistant powered by SarvamAI, Mistral, ElevenLabs, and Sesame AI CSM.",
    author="Neelaksh Saxena",
    packages=find_packages(),
    include_package_data=True,
    install_requires=required_packages,
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "shrudaya=main:main"  # Replace `main` if your script is named differently
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
