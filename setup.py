from setuptools import find_packages, setup, Extension

c_modules = Extension(
    'georouter.path_finding',
    sources=['georouter/path_finding.c'],
    include_dirs=['env_routinglib'],
    extra_compile_args=['-std=c99']
)
setup(
    name='georouter',
    packages=find_packages(include=['georouter']),
    version='0.1.6',
    description='Library for generating routes through different preferred environment attributes',
    author='David Saldubehere',
    install_requires=['requests','numpy', 'pandas', 'scipy', 'scikit-learn', 'scikit-image', 'pyrosm', 'python-igraph'],
    extras_require={
        'dev': ['pytest'],
    },
    ext_modules=[c_modules],
)