from ckan import model
from ckan.plugins.toolkit import request, config, g, get_action
from ckan.plugins import plugin_loaded
from ckanext.scheming.helpers import scheming_get_dataset_schema

import logging
log = logging.getLogger(__name__)

def append_package_value(package, edit_params):
    field = edit_params.get('field')
    languages = edit_params.get('languages')
    format_as_tags = edit_params.get('format_as_tags')

    # Update dictionary format value if field consists of multiple languages
    if len(languages) > 0 and not format_as_tags:
        value = {}
        for language in edit_params['languages']:
            key = field + '-' + language
            language_value =  package[field].get(language) + request.form[key]
            value.update({ language : language_value })

        package[field] = value
    # If the value is tag-like and consists of multiple languages, it need to be formatted as a tag list
    elif len(languages) > 0 and format_as_tags:
        value = package[field]
        for language in languages:
            key = field + '-' + language
            tag_list = request.form[key].split(",") if len(request.form[key]) > 0 else None

            # Add tags for this language only if any exist or the validation will fail later
            if tag_list:
                language_value = package[field].get(language) + tag_list if package[field].get(language) is not None else tag_list
                value.update({ language : language_value })

        package[field] = value
    elif edit_params.get('field_value'):
        package[field] += edit_params['field_value']
    # Otherwise we can just append the value to the old
    else:
        if field not in package:
            package[field] = request.form[field]
        else:
            package[field] += request.form[field]

    return package




def replace_package_value(package, edit_params):
    field = edit_params.get('field')
    languages = edit_params.get('languages')
    format_as_tags = edit_params.get('format_as_tags')

    # If using fluent or fluentall extensions and trying to update multilingual fields
    if(len(languages) > 0 and not format_as_tags):
        value = {}
        for language in languages:
            key = field + '-' + language
            value.update({ language : request.form[key] })
    # If the value is tag-string list and consists of multiple languages, it needs to be formatted as a list
    elif(len(languages) > 0 and format_as_tags):
        value = {}
        for language in languages:
            key = field + '-' + language

            # Replace old value with an empty list if a tag was not entered
            language_value = request.form[key].split(",")  if len(request.form[key]) > 0 else []
            value.update({ language : language_value })

        package[field] = value
    elif edit_params.get('field_value'):
        value = edit_params['field_value']
    else:
        value = request.form[field]

    package[field] = value

    return package

def get_editable_fields():
    scheming_schema = scheming_get_dataset_schema('dataset')['dataset_fields']

    scheming_fields = []
    for field in scheming_schema:
        scheming_fields.append({
            'field_name': field['field_name'],
            'label': field['label'],
            'form_snippet': field.get('form_snippet') if field.get('form_snippet') else 'text.html',
            'form_languages': field.get('form_languages') if field.get('form_languages') else [],
            'form_attrs': field.get('form_attrs') if field.get('form_attrs') else {},
            'format_as_tags': True if field.get('form_attrs', {}).get('data-module-tags', None) is not None else False
        })

    # Strip out fields that are not configured to be editable
    allowed_fields = config.get('ckanext.editor.editable_fields')
    fields = []

    for field in scheming_fields:
        if field['field_name'] in allowed_fields:
            fields.append(field)

    # The extension supports also group editing if enabled in the config
    if config.get('ckanext.editor.enable_group_editing'):
        context = {'model': model, 'session': model.Session,
                   'user': g.user, 'for_view': True,
                   'auth_user_obj': g.userobj, 'use_cache': False}

        users_groups = get_action('group_list_authz')(context, {})

        g.group_dropdown = [[group['id'], group['display_name']]
                            for group in users_groups if
                            group['type'] == 'group']

        group_field = {
            'field_name': 'group',
            'label': 'Group',
            'form_snippet': 'group.html',
            'form_languages': [],
            'form_attrs': {},
            'format_as_tags': False,
            'removable_value': True
        }

        fields.append(group_field)

    # Add an editable field for collections if enabled
    # Requires ckanext-collection: https://github.com/6aika/ckanext-collection
    if config.get('ckanext.editor.enable_collection_editing') and plugin_loaded('collection'):
        context = {'model': model, 'session': model.Session,
                   'user': g.user, 'for_view': True,
                   'auth_user_obj': g.userobj, 'use_cache': False}

        users_groups = get_action('group_list_authz')(context, {})

        g.collection_dropdown = [[group['id'], group['display_name']]
                                 for group in users_groups if
                                 group['type'] == 'collection']

        collection_field = {
            'field_name': 'collection',
            'label': 'Collection',
            'form_snippet': 'collection.html',
            'form_languages': [],
            'form_attrs': {},
            'format_as_tags': False,
            'removable_value': True
        }

        fields.append(collection_field)
    elif config.get('ckanext.editor.enable_collection_editing') and not plugin_loaded('collection'):
        log.error("Plugin ckanext-collection not loaded")

    return fields

def selected_field():

    # Set default field to selection
    default_field = request.args.get('_field') if request.args.get('_field') else config.get('ckanext.editor.default_field')
    _selected_field = {}
    for field in g.editable_fields:
        if field.get('field_name') == default_field:
            _selected_field = field

    # Check if the currently selected field type has a type of value that can be appended by a newly entered value
    # Groups and certain other fields are always appendable but not replaceable
    if _selected_field.get('field_name') in config.get('ckanext.editor.appendable_fields') \
            or _selected_field.get('field_name') == 'group' \
            or _selected_field.get('field_name') == 'collection':
        selected_field_appendable = True
    else:
        selected_field_appendable = False

    return _selected_field, selected_field_appendable



