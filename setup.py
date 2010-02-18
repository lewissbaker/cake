if __name__ == "__main__":
  import ez_setup
  ez_setup.use_setuptools()
  
  import sys
  import os.path
  sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
  import cake
  
  from setuptools import setup, find_packages
  setup(
    name='Cake',
    version=cake.__version__,
    description="A Python build tool.",
    license="MIT",
    package_dir={'' : 'src'},
    packages=find_packages('src', exclude=['*.test', '*.test.*']),
    entry_points={
      'console_scripts': [
        'cake = cakemain:run',
        ],
      }
    )

  sys.exit(0)