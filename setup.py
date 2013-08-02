#!/usr/bin/env python

# -*- coding: utf-8 -*-

from distutils.core import setup



setup(name='FileWatcher',
		version='1.00',
		description='File watching framework',
		packages=['filewatcher', ],
		package_dir={'': 'lib'},
		requires=['PyYAML (>=3.09)', ],
		install_requires=['PyYAML >= 3.09', ],
		classifiers=['Development Status :: 5 - Production/Stable',
			'Intended Audience :: Developers',
			'License :: OSI Approved :: MIT License',
			'Operating System :: POSIX',
			'Programming Language :: Python :: 2.6',
			'Programming Language :: Python :: 2.7', ],
		license='MIT License',
	)



# vim: ts=4 sw=4 ai nowrap
