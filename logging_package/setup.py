from setuptools import setup, find_packages

setup(
    name='my_logging',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'python-json-logger',
    ],
    include_package_data=True,
    package_data={
        '': ['config.json'],
    },
    entry_points={
        'console_scripts': [
            'setup_logging=my_logging.logger:setup_logging',
        ],
    },
)