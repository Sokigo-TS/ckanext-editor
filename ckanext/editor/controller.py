from ckanext.scheming.helpers import scheming_get_dataset_schema
from urllib import urlencode
from paste.deploy.converters import asbool
from pylons import config
from ckan.common import OrderedDict, g, request

import ckan.lib.base as base
import logging
import ckan.lib.helpers as h
import ckan.logic as logic
import ckan.authz as authz
import ckan.plugins as p
import ckan.plugins.toolkit as toolkit
import ckan.model as model
import ckan.lib.maintain as maintain
import ckan
import ast

_ = toolkit._
c = toolkit.c

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action
abort = base.abort
render = base.render
lookup_package_plugin = ckan.lib.plugins.lookup_package_plugin

log = logging.getLogger(__name__)

def _encode_params(params):
    return [(k, v.encode('utf-8') if isinstance(v, basestring) else str(v))
            for k, v in params]

def search_url(params):
    params = _encode_params(params)
    return 'editor' + u'?' + urlencode(params)

def append_package_value(package, edit_params):
    field = edit_params.get('field')
    languages = edit_params.get('languages')
    format_as_tags = edit_params.get('format_as_tags')

    # Update dictionary format value if field consists of multiple languages
    if(len(languages) > 0 and not format_as_tags):
        value = {}
        for language in edit_params['languages']:
            key = field + '-' + language
            language_value =  package[field].get(language) + request.POST[key]
            value.update({ language : language_value })

        package[field] = value
    # If the value is tag-like and consists of multiple languages, it need to be formatted as a tag list
    elif(len(languages) > 0 and format_as_tags):
        value = package[field]
        for language in languages:
            key = field + '-' + language
            tag_list = request.POST[key].split(",") if len(request.POST[key]) > 0 else None

            # Add tags for this language only if any exist or the validation will fail later
            if tag_list:
                language_value = package[field].get(language) + tag_list if package[field].get(language) is not None else tag_list
                value.update({ language : language_value })

        package[field] = value
    elif edit_params.get('field_value'):
        package[field] += edit_params['field_value']
    # Otherwise we can just append the value to the old
    else:
        package[field] += request.POST[field]

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
            value.update({ language : request.POST[key] })
    # If the value is tag-string list and consists of multiple languages, it needs to be formatted as a list
    elif(len(languages) > 0 and format_as_tags):
        value = {}
        for language in languages:
            key = field + '-' + language

            # Replace old value with an empty list if a tag was not entered
            language_value = request.POST[key].split(",")  if len(request.POST[key]) > 0 else []
            value.update({ language : language_value })

        package[field] = value
    elif edit_params.get('field_value'):
        value = edit_params['field_value']
    else:
        value = request.POST[field]

    package[field] = value

    return package

class EditorController(p.toolkit.BaseController):

    def _setup_template_variables(self, context, data_dict, package_type=None):
        return lookup_package_plugin(package_type).\
            setup_template_variables(context, data_dict)

    # Returns the search template path
    def _search_template(self, package_type):
        return 'editor/editor_base.html'

    def get_editable_fields(self):
        scheming_schema = scheming_get_dataset_schema('dataset')['dataset_fields']

        scheming_fields = []
        for field in scheming_schema:
            scheming_fields.append({
                'field_name': field['field_name'].encode('utf8'),
                'label': field['label'].encode('utf8'),
                'form_snippet': field.get('form_snippet').encode('utf8') if field.get('form_snippet') else 'text.html',
                'form_languages': field.get('form_languages') if field.get('form_languages') else [],
                'form_attrs': field.get('form_attrs') if field.get('form_attrs') else {},
                'format_as_tags': True if field.get('form_attrs', {}).get('data-module-tags', None) is not None else False
            })

        # Strip out fields that are not configured to be editable
        allowed_fields = config.get('ckanext.editor.editable_fields')
        fields = []

        for field in scheming_fields:
            if(field['field_name'] in allowed_fields):
                fields.append(field)

        # The extension supports also group editing if enabled in the config
        if config.get('ckanext.editor.enable_group_editing'):
            context = {'model': model, 'session': model.Session,
                       'user': c.user, 'for_view': True,
                       'auth_user_obj': c.userobj, 'use_cache': False}

            users_groups = get_action('group_list_authz')(context, {})

            c.group_dropdown = [[group['id'], group['display_name']]
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
        if config.get('ckanext.editor.enable_collection_editing') and p.plugin_loaded('collection'):
            context = {'model': model, 'session': model.Session,
                       'user': c.user, 'for_view': True,
                       'auth_user_obj': c.userobj, 'use_cache': False}

            users_groups = get_action('group_list_authz')(context, {})

            c.collection_dropdown = [[group['id'], group['display_name']]
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
        elif config.get('ckanext.editor.enable_collection_editing') and not p.plugin_loaded('collection'):
            log.error("Plugin ckanext-collection not loaded")

        return fields

    def package_search(self):
        if not authz.is_sysadmin(c.user):
            return abort(403, _('Not authorized to see this page'))

        # Gather extension specific search parameters etc.
        c.editable_fields = self.get_editable_fields()

        # Set default field to selection
        default_field = request.params.get('_field') if request.params.get('_field') else config.get('ckanext.editor.default_field')
        c.selected_field = {}
        for field in c.editable_fields:
            if(field.get('field_name') == default_field):
                c.selected_field = field

        # Check if the currently selected field type has a type of value that can be appended by a newly entered value
        # Groups and certain other fields are always appendable but not replaceable
        if c.selected_field.get('field_name') in config.get('ckanext.editor.appendable_fields') \
                or c.selected_field.get('field_name') == 'group' \
                or c.selected_field.get('field_name') == 'collection':
            c.selected_field_appendable = True
        else:
            c.selected_field_appendable = False

        # The search functionality is similar to CKAN package search in ckan/controllers/package.py
        # This might need updating if the core package search functionality is changed after v2.5
        from ckan.lib.search import SearchError, SearchQueryError

        package_type = 'dataset'

        try:
            context = {'model': model, 'user': c.user,
                       'auth_user_obj': c.userobj}
            check_access('site_read', context)
        except NotAuthorized:
            abort(403, _('Not authorized to see this page'))

        # unicode format (decoded from utf8)
        q = c.q = request.params.get('q', u'')
        c.query_error = False

        try:
            page = self._get_page_number(request.params)
        except AttributeError:
            # in CKAN >= 2.5 _get_page_number has been moved
            page = h.get_page_number(request.params)

        limit = g.datasets_per_page

        # most search operations should reset the page counter:
        params_nopage = [(k, v) for k, v in request.params.items()
                         if k != 'page']

        def drill_down_url(alternative_url=None, **by):
            return h.add_url_param(alternative_url=alternative_url,
                                   controller='package', action='search',
                                   new_params=by)

        c.drill_down_url = drill_down_url

        def remove_field(key, value=None, replace=None):
            return h.remove_url_param(key, value=value, replace=replace,
                                      controller='package', action='search')

        c.remove_field = remove_field

        sort_by = request.params.get('sort', None)
        params_nosort = [(k, v) for k, v in params_nopage if k != 'sort']

        def _sort_by(fields):
            """
            Sort by the given list of fields.
            Each entry in the list is a 2-tuple: (fieldname, sort_order)
            eg - [('metadata_modified', 'desc'), ('name', 'asc')]
            If fields is empty, then the default ordering is used.
            """
            params = params_nosort[:]

            if fields:
                sort_string = ', '.join('%s %s' % f for f in fields)
                params.append(('sort', sort_string))
            return search_url(params)

        c.sort_by = _sort_by
        if not sort_by:
            c.sort_by_fields = []
        else:
            c.sort_by_fields = [field.split()[0]
                                for field in sort_by.split(',')]

        def pager_url(q=None, page=None):
            params = list(params_nopage)
            params.append(('page', page))
            return search_url(params)

        c.search_url_params = urlencode(_encode_params(params_nopage))

        try:
            c.fields = []
            # c.fields_grouped will contain a dict of params containing
            # a list of values eg {'tags':['tag1', 'tag2']}
            c.fields_grouped = {}
            search_extras = {}
            fq = ''
            for (param, value) in request.params.items():
                if param not in ['q', 'page', 'sort'] \
                        and len(value) and not param.startswith('_'):
                    if not param.startswith('ext_'):
                        c.fields.append((param, value))
                        fq += ' %s:"%s"' % (param, value)
                        if param not in c.fields_grouped:
                            c.fields_grouped[param] = [value]
                        else:
                            c.fields_grouped[param].append(value)
                    else:
                        search_extras[param] = value

            context = {'model': model, 'session': model.Session,
                       'user': c.user, 'for_view': True,
                       'auth_user_obj': c.userobj}

            if package_type and package_type != 'dataset':
                # Only show datasets of this particular type
                fq += ' +dataset_type:{type}'.format(type=package_type)
            else:
                # Unless changed via config options, don't show non standard
                # dataset types on the default search page
                if not asbool(
                        config.get('ckan.search.show_all_types', 'False')):
                    fq += ' +dataset_type:dataset'

            facets = OrderedDict()

            default_facet_titles = {
                'organization': _('Organizations'),
                'groups': _('Groups'),
                'tags': _('Tags'),
                'res_format': _('Formats'),
                'license_id': _('Licenses'),
                }

            for facet in g.facets:
                if facet in default_facet_titles:
                    facets[facet] = default_facet_titles[facet]
                else:
                    facets[facet] = facet

            # Facet titles
            for plugin in p.PluginImplementations(p.IFacets):
                facets = plugin.dataset_facets(facets, package_type)

            c.facet_titles = facets

            data_dict = {
                'q': q,
                'fq': fq.strip(),
                'facet.field': facets.keys(),
                'rows': limit,
                'start': (page - 1) * limit,
                'sort': sort_by,
                'extras': search_extras,
            }

            # Include private is added in CKAN v2.6
            if(toolkit.check_ckan_version('2.6')):
                data_dict['include_private'] = True

            query = get_action('package_search')(context, data_dict)
            c.sort_by_selected = query['sort']

            c.page = h.Page(
                collection=query['results'],
                page=page,
                url=pager_url,
                item_count=query['count'],
                items_per_page=limit
            )
            c.facets = query['facets']
            c.search_facets = query['search_facets']
            c.page.items = query['results']
        except SearchQueryError, se:
            # User's search parameters are invalid, in such a way that is not
            # achievable with the web interface, so return a proper error to
            # discourage spiders which are the main cause of this.
            log.info('Dataset search query rejected: %r', se.args)
            abort(400, _('Invalid search query: {error_message}')
                  .format(error_message=str(se)))
        except SearchError, se:
            # May be bad input from the user, but may also be more serious like
            # bad code causing a SOLR syntax error, or a problem connecting to
            # SOLR
            log.error('Dataset search error: %r', se.args)
            c.query_error = True
            c.facets = {}
            c.search_facets = {}
            c.page = h.Page(collection=[])
        c.search_facets_limits = {}
        for facet in c.search_facets.keys():
            try:
                limit = int(request.params.get('_%s_limit' % facet,
                                               g.facets_default_number))
            except ValueError:
                abort(400, _('Parameter "{parameter_name}" is not '
                             'an integer').format(
                      parameter_name='_%s_limit' % facet))
            c.search_facets_limits[facet] = limit

        maintain.deprecate_context_item(
            'facets',
            'Use `c.search_facets` instead.')

        self._setup_template_variables(context, {},
                                       package_type=package_type)

        return render(self._search_template(package_type),
                      extra_vars={'dataset_type': package_type})


    def package_update(self):
        context = {'model': model, 'user': c.user, 'auth_user_obj': c.userobj}
        edit_params = {}

        if not authz.is_sysadmin(c.user):
            abort(403, _('Not authorized to see this page'))

        try:
            edit_params = {
                'package_ids': request.POST.getall('package_id'),
                'field': request.POST['field'],
                'edit_action': request.POST['edit_action'],
                'format_as_tags': ast.literal_eval(request.POST['format_as_tags']),
                'languages': ast.literal_eval(request.POST['form_languages'].encode('utf8'))
            }

            # External_urls field needs to be handled separately since it can contain multiple
            # values with the same key
            values = []
            if(edit_params['field'] == 'external_urls'):
                for k, v in request.POST.iteritems():
                    if k == 'external_urls':
                        values.append(v)
                edit_params['field_value'] = values

        except ValidationError:
            return abort(409, _('Validation error'))
        except KeyError:
            return abort(400, _('Key error'))

        for id in edit_params['package_ids']:
            try:
                package = toolkit.get_action('package_show')(context, { 'id': id })

                # Groups and collections need special treatment since not included in the data model
                # and thus cannot be updated with package_update
                if edit_params['field'] == 'group' or edit_params['field'] == 'collection':
                    context = {'model': model, 'session': model.Session,
                               'user': c.user, 'for_view': True,
                               'auth_user_obj': c.userobj, 'use_cache': False}

                    group_ref = request.POST.get('group')

                    data_dict = {"id": group_ref,
                                 "object": id,
                                 "object_type": 'package',
                                 "capacity": 'public'}
                    try:
                        if(edit_params['edit_action'] == 'append'):
                            get_action('member_create')(context, data_dict)
                        elif(edit_params['edit_action'] == 'remove'):
                            get_action('member_delete')(context, data_dict)
                    except NotFound:
                        abort(404, _('Group not found'))

                # All other types of fields can be updated with package_update
                else:
                    # Append the new value to the old field value if requested
                    if(edit_params['edit_action'] == 'append'):
                        package = append_package_value(package, edit_params)
                    elif(edit_params['edit_action'] == 'remove'):
                        log.info("Remove action not supported for other fields than group and collection")
                    # Replace the old field value entirely
                    elif(edit_params['edit_action'] == 'replace'):
                        package = replace_package_value(package, edit_params)
                    else:
                        log.error('Provided edit action "' + edit_params['edit_action'] + '" not supported')

                    toolkit.get_action('package_update')(context, package)
            except NotAuthorized:
                return abort(403, _('Not authorized to see this page'))
            except NotFound:
                return abort(404, _('Package not found'))
            except ValidationError:
                return abort(409, _('Validation error'))

        h.redirect_to('/editor?_field=' + edit_params['field'].encode('utf8'))
        return render('editor/editor_base.html')