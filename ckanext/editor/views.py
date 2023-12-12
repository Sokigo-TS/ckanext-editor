import ast
from collections import OrderedDict
from functools import partial

import six
from ckan import model
from ckan.lib.search import SearchQueryError, SearchError

from flask import Blueprint
import ckan.lib.helpers as h
import ckan.plugins as plugins
from ckan.plugins import toolkit

from ckan.lib.plugins import lookup_package_plugin
from ckan.views.dataset import drill_down_url, remove_field, _sort_by, _pager_url, _encode_params, _get_search_details
from flask.views import MethodView

from six.moves.urllib.parse import urlencode
from .utils import append_package_value, replace_package_value, get_editable_fields, selected_field

check_access = toolkit.check_access
get_action = toolkit.get_action
g = toolkit.g
NotAuthorized = toolkit.NotAuthorized
ValidationError = toolkit.ValidationError
NotFound = toolkit.ObjectNotFound
abort = toolkit.abort
render = toolkit.render
_ = toolkit._
config = toolkit.config
request = toolkit.request
asbool = toolkit.asbool


import logging
log = logging.getLogger(__name__)


editor = Blueprint('editor', __name__)

def _setup_template_variables(context, data_dict, package_type=None):
    return lookup_package_plugin(package_type). \
        setup_template_variables(context, data_dict)



class EditorView(MethodView):
    def get(self):
        try:
            context = dict(model=model, user=g.user, auth_user_obj=g.userobj)
            check_access('sysadmin', context)
        except NotAuthorized:
            return abort(403, _('Not authorized to see this page'))

        # Gather extension specific search parameters etc.
        g.editable_fields = get_editable_fields()


        g.selected_field, g.selected_field_appendable = selected_field()


        try:
            context = {'model': model, 'user': g.user,
                       'auth_user_obj': g.userobj}
            check_access('site_read', context)
        except NotAuthorized:
            abort(403, _('Not authorized to see this page'))

        package_type = 'dataset'

        extra_vars = _search()

        _setup_template_variables(context, {},
                                  package_type=package_type)

        return render('editor/editor_base.html',
                      extra_vars=extra_vars)


    def post(self):
        context = {'model': model, 'user': g.user, 'auth_user_obj': g.userobj, 'keep_deletable_attributes_in_api': True}
        edit_params = {}

        try:
            check_access('sysadmin', context)
        except NotAuthorized:
            abort(403, _('Not authorized to see this page'))

        try:
            edit_params = {
                'package_ids': request.form.getlist('package_id'),
                'field': request.form['field'],
                'edit_action': request.form['edit_action'],
                'format_as_tags': ast.literal_eval(request.form['format_as_tags']),
                'languages': ast.literal_eval(request.form['form_languages'])
            }

            # External_urls field needs to be handled separately since it can contain multiple
            # values with the same key
            values = []
            if edit_params['field'] == 'external_urls':
                for k, v in request.form.items():
                    if k == 'external_urls':
                        values.append(v)
                edit_params['field_value'] = values

        except ValidationError:
            return abort(409, _('Validation error'))
        except KeyError as e:
            toolkit.redirect_to('editor.search', **request.params)

        formats = []
        coverages = []
        groups = []
        organizations = []
        collections = []
        for k, v in request.params.items():
            if k == 'res_format':
                formats.append(v)
            elif k == 'vocab_geographical_coverage':
                coverages.append(v)
            elif k == 'groups':
                groups.append(v)
            elif k == 'organization':
                organizations.append(v)
            elif k == 'collections':
                collections.append(v)

        for id in edit_params['package_ids']:
            try:
                package = toolkit.get_action('package_show')(context, { 'id': id })

                # Groups and collections need special treatment since not included in the data model
                # and thus cannot be updated with package_update
                if edit_params['field'] == 'group' or edit_params['field'] == 'collection':
                    context = {'model': model, 'session': model.Session,
                               'user': g.user, 'for_view': True,
                               'auth_user_obj': g.userobj, 'use_cache': False}

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
            except ValidationError as e:
                errors = e.error_dict
                error_summary = e.error_summary
                g.editable_fields = get_editable_fields()
                g.selected_field, g.selected_field_appendable  = selected_field()

                extra_vars = _search()
                extra_vars['errors'] = errors
                extra_vars['error_summary'] = error_summary
                return render('editor/editor_base.html', extra_vars=extra_vars)

        g.editable_fields = get_editable_fields()
        g.selected_field, g.selected_field_appendable  = selected_field()
        extra_vars = _search()
        return render('editor/editor_base.html',
                      extra_vars=extra_vars)


editor.add_url_rule('/editor', view_func=EditorView.as_view('search'), methods=["GET", "POST"])

def _search():

    package_type = 'dataset'

    extra_vars = {}

    try:
        context = {
            u'model': model,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
        check_access(u'site_read', context)
    except NotAuthorized:
        abort(403, _(u'Not authorized to see this page'))

    # unicode format (decoded from utf8)
    extra_vars[u'q'] = q = request.args.get(u'q', u'')

    extra_vars['query_error'] = False
    page = h.get_page_number(request.args)

    limit = int(config.get(u'ckan.datasets_per_page', 20))

    # most search operations should reset the page counter:
    params_nopage = [(k, v) for k, v in request.args.items(multi=True)
                     if k != u'page']

    extra_vars[u'drill_down_url'] = drill_down_url
    extra_vars[u'remove_field'] = partial(remove_field, package_type)

    sort_by = request.args.get(u'sort', None)
    params_nosort = [(k, v) for k, v in params_nopage if k != u'sort']

    extra_vars[u'sort_by'] = partial(_sort_by, params_nosort, package_type)

    if not sort_by:
        sort_by_fields = []
    else:
        sort_by_fields = [field.split()[0] for field in sort_by.split(u',')]
    extra_vars[u'sort_by_fields'] = sort_by_fields

    pager_url = partial(_pager_url, params_nopage, "editor")

    search_url_params = urlencode(_encode_params(params_nopage))
    extra_vars[u'search_url_params'] = search_url_params

    details = _get_search_details()
    extra_vars[u'fields'] = details[u'fields']
    extra_vars[u'fields_grouped'] = details[u'fields_grouped']
    fq = details[u'fq']
    search_extras = details[u'search_extras']

    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'for_view': True,
        u'auth_user_obj': g.userobj
    }

    # Unless changed via config options, don't show other dataset
    # types any search page. Potential alternatives are do show them
    # on the default search page (dataset) or on one other search page
    search_all_type = config.get(u'ckan.search.show_all_types', u'dataset')
    search_all = False

    try:
        # If the "type" is set to True or False, convert to bool
        # and we know that no type was specified, so use traditional
        # behaviour of applying this only to dataset type
        search_all = asbool(search_all_type)
        search_all_type = u'dataset'
    # Otherwise we treat as a string representing a type
    except ValueError:
        search_all = True

    if not search_all or package_type != search_all_type:
        # Only show datasets of this particular type
        fq += u' +dataset_type:{type}'.format(type=package_type)

    facets = OrderedDict()

    default_facet_titles = {
        u'organization': _(u'Organizations'),
        u'groups': _(u'Groups'),
        u'tags': _(u'Tags'),
        u'res_format': _(u'Formats'),
        u'license_id': _(u'Licenses'),
    }

    for facet in h.facets():
        if facet in default_facet_titles:
            facets[facet] = default_facet_titles[facet]
        else:
            facets[facet] = facet

    # Facet titles
    for plugin in plugins.PluginImplementations(plugins.IFacets):
        facets = plugin.dataset_facets(facets, package_type)

    extra_vars[u'facet_titles'] = facets
    data_dict = {
        u'q': q,
        u'fq': fq.strip(),
        u'facet.field': list(facets.keys()),
        u'rows': limit,
        u'start': (page - 1) * limit,
        u'sort': sort_by,
        u'extras': search_extras,
        u'include_private': asbool(
            config.get(u'ckan.search.default_include_private', True)
        ),
    }
    try:
        query = get_action(u'package_search')(context, data_dict)

        extra_vars[u'sort_by_selected'] = query[u'sort']

        extra_vars[u'page'] = h.Page(
            collection=query[u'results'],
            page=page,
            url=pager_url,
            item_count=query[u'count'],
            items_per_page=limit
        )
        extra_vars[u'search_facets'] = query[u'search_facets']
        extra_vars[u'page'].items = query[u'results']
    except SearchQueryError as se:
        # User's search parameters are invalid, in such a way that is not
        # achievable with the web interface, so return a proper error to
        # discourage spiders which are the main cause of this.
        log.info(u'Dataset search query rejected: %r', se.args)
        abort(
            400,
            _(u'Invalid search query: {error_message}')
            .format(error_message=str(se))
        )
    except SearchError as se:
        # May be bad input from the user, but may also be more serious like
        # bad code causing a SOLR syntax error, or a problem connecting to
        # SOLR
        log.error(u'Dataset search error: %r', se.args)
        extra_vars[u'query_error'] = True
        extra_vars[u'search_facets'] = {}
        extra_vars[u'page'] = h.Page(collection=[])

    # FIXME: try to avoid using global variables
    g.search_facets_limits = {}
    for facet in extra_vars[u'search_facets'].keys():
        try:
            limit = int(
                request.args.get(
                    u'_%s_limit' % facet,
                    int(config.get(u'search.facets.default', 10))
                )
            )
        except ValueError:
            abort(
                400,
                _(u'Parameter u"{parameter_name}" is not '
                  u'an integer').format(parameter_name=u'_%s_limit' % facet)
            )

        g.search_facets_limits[facet] = limit

    _setup_template_variables(context, {}, package_type=package_type)

    extra_vars[u'dataset_type'] = package_type

    # TODO: remove
    for key, value in six.iteritems(extra_vars):
        setattr(g, key, value)

    return extra_vars
