import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.lib.plugins import DefaultTranslation
from ckanext.editor import helpers
from .views import editor as editor_blueprint


class EditorPlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IRoutes, inherit=True)
    if toolkit.check_ckan_version(min_version='2.5.0'):
        plugins.implements(plugins.ITranslation, inherit=True)
    plugins.implements(plugins.IBlueprint)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_resource('fanstatic', 'editor')

    # IConfigurable

    def configure(self, config):
        # Raise an exception if required configs are missing
        required_keys = [
            'ckanext.editor.editable_fields',
            'ckanext.editor.default_field',
            'ckanext.editor.appendable_fields'
        ]

        for key in required_keys:
            if config.get(key) is None:
                raise RuntimeError(
                    'Required configuration option {0} not found.'.format(
                        key
                    )
                )

    def get_helpers(self):
        return {'get_group_names_for_package': helpers.get_group_names_for_package}

    # IBlueprint

    def get_blueprint(self):
        return [editor_blueprint]
