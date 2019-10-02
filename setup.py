from setuptools import setup, find_packages
import versioneer


def readme():
    with open('readme.rst') as f:
        return f.read()


setup(name='qcodes_contrib_drivers',
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      use_2to3=False,

      maintainer='Jens H Nielsen',
      maintainer_email='Jens.Nielsen@microsoft.com',
      description='User contributed drivers for QCoDeS',
      long_description=readme(),
      url='https://github.com/QCoDeS/Qcodes_contrib_drivers',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Science/Research',
          'Programming Language :: Python :: 3 :: Only',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Topic :: Scientific/Engineering'
      ],
      license='MIT',
      packages=find_packages(),
      install_requires=[
          'qcodes>=0.4.0',
      ],
      zip_safe=False)
