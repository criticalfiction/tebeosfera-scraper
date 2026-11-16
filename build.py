#!/usr/bin/env python
'''
Build script for the Tebeosfera Scraper ComicRack plugin.

Creates a .crplugin file (which is just a ZIP archive) from the contents
of the src/ directory.

Usage:
    python build.py

This will create TebeosferaScraper-<version>.crplugin in the build/ directory.
'''

import os
import sys
import zipfile
import shutil

# Handle both Python 2 and 3
try:
    import configparser
except ImportError:
    import ConfigParser as configparser

# ===========================================================================

SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
BUILD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build')

# Files to exclude from the .crplugin
EXCLUDE_FILES = {
    '__init__.py',
    '.gitignore',
    '.git',
    'tests',
}


# ===========================================================================
def read_package_ini():
    '''Reads metadata from src/Package.ini'''
    ini_path = os.path.join(SRC_DIR, 'Package.ini')
    # Package.ini is not a standard INI (no section headers), so we read
    # it manually (simple key = value format)
    meta = {
        'Name': 'Tebeosfera Scraper',
        'Version': '0.0.0',
        'Author': 'Unknown',
        'Description': '',
    }
    with open(ini_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip()
                if key in meta:
                    meta[key] = val
    return meta


# ===========================================================================
def build_plugin():
    '''Builds the .crplugin file from src/ contents.'''
    meta = read_package_ini()
    name = meta['Name']
    version = meta['Version']

    # Clean and create build directory
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    os.makedirs(BUILD_DIR)

    # Output filename
    safe_name = name.replace(' ', '')
    output_file = os.path.join(BUILD_DIR,
                               '%s-%s.crplugin' % (safe_name, version))

    # Collect all files from src/
    plugin_files = []
    for item in os.listdir(SRC_DIR):
        item_path = os.path.join(SRC_DIR, item)
        basename = os.path.basename(item)

        # Skip excluded files
        if basename in EXCLUDE_FILES:
            continue
        if basename.endswith('.pyc') or basename.endswith('.pyo'):
            continue
        if basename.startswith('.'):
            continue

        if os.path.isfile(item_path):
            plugin_files.append(basename)

    # Create the ZIP file
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename in sorted(plugin_files):
            filepath = os.path.join(SRC_DIR, filename)
            # Store with just the basename (flat structure, as ComicRack expects)
            zf.write(filepath, filename)

    print('Built: %s' % output_file)
    print('  Name: %s' % name)
    print('  Version: %s' % version)
    print('  Files: %d' % len(plugin_files))
    print('  Size: %d bytes' % os.path.getsize(output_file))

    return output_file


# ===========================================================================
if __name__ == '__main__':
    build_plugin()
