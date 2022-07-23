from setuptools import setup

setup(
    name="hibye",
    description='simple request-response services in python',
    author='Daniel Dugas',
    version='0.0.1',
    packages=["hibye"],
#     ext_modules=cythonize("something/something.pyx", annotate=True),
    python_requires='>=3.6',
    install_requires=[
        'numpy',
        'matplotlib',
        'socket',
        'json'
    ],
#     include_dirs=[numpy.get_include()],
#     package_data={'navrep': ['maps/*']},
)
