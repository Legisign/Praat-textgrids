#!/usr/bin/env python3
'''

   praat-textgrids

   Python module for manipulating Praat text-format TextGrid files.
   Copyright © 2019 Legisign.org, Tommi Nieminen <software@legisign.org>

   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see <https://www.gnu.org/licenses/>.

  2020-01-21  1.3.0    Automatic file type detection.

'''

import setuptools

with open('README.md', 'r') as readme:
    long_description = readme.read()

setuptools.setup(name='praat-textgrids',
                 version='1.3.1',
                 description='Manipulation of Praat TextGrids',
                 long_description=long_description,
                 long_description_content_type='text/markdown',
                 url='http://github.com/Legisign/Praat-textgrids',
                 author='Legisign.org',
                 author_email='software@legisign.org',
                 license='GPLv3',
                 packages=setuptools.find_packages())
