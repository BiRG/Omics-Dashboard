from dash import Dash
from dash.exceptions import PreventUpdate
from dash_bootstrap_components.themes import FLATLY, DARKLY
from flask_login import current_user


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

    @staticmethod
    def check_clicks(n_clicks):
        if not n_clicks:
            raise PreventUpdate('Callback triggered without action!')

    @staticmethod
    def check_dropdown(value):
        if not value or None in value:
            raise PreventUpdate('Callback triggered without action!')


class StyledDash(Dash):
    def interpolate_index(self, **kwargs):
        style_url = DARKLY if current_user and current_user.theme == 'dark' else FLATLY
        dark_css = '''
        <style>
          .form-group .VirtualizedSelectOption {
            background-color: #FFFFFF;
            color: #303030;
          }
          .form-group .VirtualizedSelectFocusedOption {
            background-color: #F0544C;
            color: #FFFFFF;
          }
        </style>
        ''' if current_user and current_user.theme == 'dark' else ''
        return f'''
        <!DOCTYPE html>
        <html>
            <head>
                <link href="{style_url}" rel="stylesheet">
                {dark_css}
                <title>{kwargs["title"]}</title>
            </head>
            <body>
                {kwargs["app_entry"]}
                {kwargs["config"]}
                {kwargs["scripts"]}
                {kwargs["renderer"]}
            </body>
        </html>
        '''


def get_plot_theme():
    try:
        return 'plotly_dark' if current_user and current_user.theme == 'dark' else 'plotly_white'
    except:
        return 'plotly_white'
