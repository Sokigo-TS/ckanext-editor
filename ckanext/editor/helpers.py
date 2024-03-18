import logging
import ckan.lib.base as base
import ckan.logic as logic
import ckan.model as model
from ckan.model.package import Package
from ckan.lib.dictization.model_dictize import group_list_dictize

NotFound = logic.NotFound
abort = base.abort

log = logging.getLogger(__name__)

from ckantoolkit import config, _
import six

all_helpers = {}

def helper(fn):
    """
    collect helper functions into ckanext.editor.all_helpers dict
    """
    all_helpers[fn.__name__] = fn
    return fn


def lang():
    # access this function late in case ckan
    # is not set up fully when importing this module
    from ckantoolkit import h
    return h.lang()

@helper
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
    
@helper
def scheming_language_text(text, prefer_lang=None):
    """
    :param text: {lang: text} dict or text string
    :param prefer_lang: choose this language version if available

    Convert "language-text" to users' language by looking up
    languag in dict or using gettext if not a dict
    """
    if not text:
        return u''

    assert text != {}
    if hasattr(text, 'get'):
        try:
            if prefer_lang is None:
                prefer_lang = lang()
        except TypeError:
            pass  # lang() call will fail when no user language available
        else:
            try:
                return text[prefer_lang]
            except KeyError:
                pass

        default_locale = config.get('ckan.locale_default', 'en')
        try:
            return text[default_locale]
        except KeyError:
            pass

        l, v = sorted(text.items())[0]
        return v

    if isinstance(text, six.binary_type):
        text = text.decode('utf-8')
    t = _(text)
    return t    