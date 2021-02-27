from setuptools import setup, find_packages


install_requires = [
    'Scrapy>=2.4.1',
    'Flask>=1.1.2',
    'Flask-RESTful>=0.3.8',
    'user-agent>=0.1.9',
    'gunicorn>=20.0.4',
    'redis>=3.5.3',
    'aiohttp>=3.7.3',
    'Werkzeug>=1.0.1'
]


setup(
    name='Nproxypool',
    version='1.0.2',
    url='https://github.com/moqsien/nproxypool',
    project_urls={
        'Documentation': 'https://github.com/moqsien/nproxypool/blob/main/README.md',
        'Source': 'https://github.com/moqsien/nproxypool',
        'Tracker': 'https://github.com/moqsien/nproxypool',
    },
    description='A Proxypool',
    author='MoQsien',
    maintainer='MoQsien',
    maintainer_email='moqsien@foxmail.com',
    packages=find_packages(exclude=('tests', 'tests.*', 'example')),
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': ['npool = nproxypool.cmdline:execute']
    },
    python_requires='>=3.6',
    install_requires=install_requires,
    extras_require={}
)
