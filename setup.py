import os
from setuptools import find_packages, setup
from asgigram import __version__


# We use the README as the long_description
readme_path = os.path.join(os.path.dirname(__file__), "README.rst")


setup(
    name='asgigram',
    version=__version__,
    url='http://github.com/andrewgodwin/asgigram/',
    author='Andrew Godwin',
    author_email='andrew@aeracode.org',
    description='ASGI/Telegram server using long-polling',
    long_description=open(readme_path).read(),
    license='BSD',
    zip_safe=False,
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    install_requires=[
        'aiohttp',
        'asgiref~=2.0',
    ],
    entry_points={'console_scripts': [
        'asgigram = asgigram.cli:CommandLineInterface.entrypoint',
    ]},
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
)
