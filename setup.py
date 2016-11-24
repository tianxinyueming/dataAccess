from distutils.core import setup
import time

setup(
    name='dataAccess',
    version='1.0.' + time.strftime('%y%m%d'),
    py_modules=['dataAccess', 'conf/config'],
    packages=['src'],
    url='',
    license='',
    author='shangxc',
    author_email='',
    description=''
)
