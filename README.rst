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

    # Default selected field when loading the editor
    ckanext.editor.default_field

    # List of fields for which new entered values can be appended to the field's old value instead of replacing the old value
    ckanext.editor.appendable_fields

    # Set this to True to enable adding/removing of groups which a dataset belongs to
    # Adds a Group-option to the editable field selection
    # Will default to False
    ckanext.editor.enable_group_editing

    # Set this to True if using ckanext-collection: https://github.com/6aika/ckanext-collection
    # Adds a Collection-option to the editable fields and makes it possible to add/remove collections similar to groups
    # Will default to False
    ckanext.editor.enable_collection_editing


---------------
Updating translations
---------------

To extract all translatable strings run this command in the plugin root directory::

    python setup.py extract_messages

After this the updated ckanext-editor.pot with the source language can be pushed to Transifex with the transifex client.
Note that you need to set your transifex credentials into ~/.transifexrc before running the command::

    tx push --source

Translate new strings in Transifex and pull them by running::

    # --force can be added if old translations can be overwritten by the ones fetched from transifex (this is usually the case)
    tx pull