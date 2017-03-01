import logging
import ckan.lib.base as base
import ckan.logic as logic
import ckan.model as model
from ckan.model.package import Package
from ckan.lib.dictization.model_dictize import group_list_dictize

NotFound = logic.NotFound
abort = base.abort

log = logging.getLogger(__name__)

def get_group_names_for_package(package_id, group_type):
    context = {'model': model, 'session': model.Session,
               'for_view': True, 'use_cache': False}

    group_list = []

    try:
        pkg_obj = Package.get(package_id)
        group_list = group_list_dictize(pkg_obj.get_groups(group_type, None), context)
    except (NotFound):
        abort(404, _('Dataset not found'))

    results = []
    for item in group_list:
        results.append(item['display_name'])
    return results