from setuptools import setup, find_packages
import os

version = '1.0b1'

setup(name='collective.contentrules.parentchild',
      version=version,
      description="Content rules conditions and actions for expressing parent/child object relationships",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Framework :: Plone",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='plone content rules',
      author='Martin Aspeli',
      author_email='optilude@gmail.com',
      url='http://pypi.python.org/pypi/collective.contentrules.parentchild',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['collective', 'collective.contentrules'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'plone.app.contentrules',
          'plone.contentrules',
      ],
      entry_points="""
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
