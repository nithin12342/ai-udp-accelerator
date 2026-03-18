#!/usr/bin/env python3
"""
Setup configuration for NetVelocity AI UDP Accelerator
"""

from setuptools import setup, find_packages

setup(
    name='netvelocity',
    version='1.0.0',
    description='AI-powered UDP acceleration with intelligent rate control',
    author='NetVelocity Engineering',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    python_requires='>=3.8',
    install_requires=[
        'psutil>=5.9.0',
    ],
    extras_require={
        'redis': ['redis>=4.5.0'],
    },
    entry_points={
        'console_scripts': [
            'netvelocity=netvelocity:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
)
