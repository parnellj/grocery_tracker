try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup

config = {
	'name': 'Grocery Inventory Tracker',
	'version': '0.1',
	'url': 'https://github.com/parnellj/grocery_tracker',
	'download_url': 'https://github.com/parnellj/grocery_tracker',
	'author': 'Justin Parnell',
	'author_email': 'parnell.justin@gmail.com',
	'maintainer': 'Justin Parnell',
	'maintainer_email': 'parnell.justin@gmail.com',
	'classifiers': [],
	'license': 'GNU GPL v3.0',
	'description': 'Enables the scanning, tracking, and prediction of a households grocery inventory.',
	'long_description': 'Enables the scanning, tracking, and prediction of a households grocery inventory.',
	'keywords': '',
	'install_requires': ['nose'],
	'packages': ['grocery_tracker'],
	'scripts': []
}
	
setup(**config)
