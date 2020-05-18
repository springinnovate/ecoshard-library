"""Setup for stac_api package."""
from setuptools import find_packages, setup

setup(
    name='stac_api',
    version='1.0.0',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'ecoshard',
        'flask',
        'gdal',
        'numpy',
        'pygeoprocessing',
        'requests',
        'retrying',
    ],
)
