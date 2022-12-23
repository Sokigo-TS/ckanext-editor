from flask import Blueprint


editor = Blueprint('editor', __name__)




def package_search(self, errors=None, error_summary=None):
    if not authz.is_sysadmin(c.user):
        return abort(403, _('Not authorized to see this page'))

    # Gather extension specific search parameters etc.
    c.editable_fields = self.get_editable_fields()

    self._selected_field()

    try:
        context = {'model': model, 'user': c.user,
                   'auth_user_obj': c.userobj}
        check_access('site_read', context)
    except NotAuthorized:
        abort(403, _('Not authorized to see this page'))

    package_type = 'dataset'

    self._search()

    self._setup_template_variables(context, {},
                                   package_type=package_type)

    return render(self._search_template(package_type),
                  extra_vars={'dataset_type': package_type, 'errors': errors, 'error_summary': error_summary})


def package_update(self):
    context = {'model': model, 'user': c.user, 'auth_user_obj': c.userobj, 'keep_deletable_attributes_in_api': True}
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
        if edit_params['field'] == 'external_urls':
            for k, v in request.POST.iteritems():
                if k == 'external_urls':
                    values.append(v)
            edit_params['field_value'] = values

    except ValidationError:
        return abort(409, _('Validation error'))
    except KeyError as e:
        h.redirect_to(controller='ckanext.editor.controller:EditorController', action='package_search', **request.params)

    formats = []
    coverages = []
    groups = []
    organizations = []
    collections = []
    for k, v in request.params.iteritems():
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
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            self._selected_field()

            self._search()
            return render('editor/editor_base.html', extra_vars={"errors": errors, "error_summary": error_summary})

    h.redirect_to(controller='ckanext.editor.controller:EditorController', action='package_search',
                  _field=edit_params['field'].encode('utf8'), res_format=formats,
                  vocab_geographical_coverage=coverages, groups=groups, organization=organizations,
                  collections=collections, q=request.params.get('q', u''), sort=request.params.get('sort', u''))


editor.add_url_rule('/editor', view_func=package_search)
editor.add_url_rule('/editor/package_update', view_func=package_update)
