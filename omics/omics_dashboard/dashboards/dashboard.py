from dash import Dash
from flask_login import current_user
from dash_bootstrap_components.themes import FLATLY, DARKLY


class Dashboard:
    name = 'Dashboard'
    prefix = '/dashboards/'
    description = 'You should overload description with the description of your dashboard.'
    id = 'dashboard'

    @staticmethod
    def create_dash_app(server):
        """
        :param server:
        :return:
        """
        raise NotImplementedError('')


class StyledDash(Dash):
    def interpolate_index(self, **kwargs):
        style_url = DARKLY if current_user and current_user.theme == 'dark' else FLATLY
        return f'''
        <!DOCTYPE html>
        <html>
            <head>
                <link href="{style_url}" rel="stylesheet">
                <title>My App</title>
            </head>
            <body>
                {kwargs["app_entry"]}
                {kwargs["config"]}
                {kwargs["scripts"]}
                {kwargs["renderer"]}
            </body>
        </html>
        '''
