from setuptools import setup, find_packages

setup(name='pyeconet',
      version='0.1.12',
      description='Interface to the unofficial EcoNet API',
      url='http://github.com/w1ll1am23/pyeconet',
      author='William Scanlon',
      license='MIT',
      install_requires=['aiohttp>=3.6.0', 'paho-mqtt>=1.5.0'],
      tests_require=['mock'],
      test_suite='tests',
      packages=find_packages(exclude=["dist", "*.test", "*.test.*", "test.*", "test"]),
      zip_safe=True)
