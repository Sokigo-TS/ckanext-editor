=============
ckanext-editor
=============

This is a CKAN extension for editing multiple datasets simultaneously.
The extension creates a route to '/editor' where you can search datasets and select a field to edit.


------------
Requirements
------------

Tested with CKAN v2.5

Requires ckanext-scheming, available at https://github.com/ckan/ckanext-scheming


------------
Installation
------------

To install ckanext-editor:

1. Activate your CKAN virtual environment, for example::

     . /usr/lib/ckan/default/bin/activate

2. Install ckanext-scheming by following the instructions available at: https://github.com/ckan/ckanext-scheming

3. Install the ckanext-editor Python package into your virtual environment::

     pip install ckanext-editor

4. Add ``editor`` to the ``ckan.plugins`` setting in your CKAN
   config file (by default the config file is located at
   ``/etc/ckan/default/production.ini``).

5. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu::

     sudo service apache2 reload


---------------
Config Settings
---------------

Required::

    # List of field_names which will be allowed to be edited by ckanext-editor
    ckanext.editor.editable_fields 