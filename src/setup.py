from setuptools import setup, find_packages

setup(name='pyeconet',
      version='0.0.11',
      description='Interface to the unofficial EcoNet API',
      url='http://github.com/w1ll1am23/pyeconet',
      author='William Scanlon',
      license='MIT',
      install_requires=['requests>=2.0', 'tzlocal', 'python-dateutil'],
      tests_require=['mock'],
      test_suite='tests',
      packages=find_packages(exclude=["dist", "*.test", "*.test.*", "test.*", "test"]),
      zip_safe=True)
