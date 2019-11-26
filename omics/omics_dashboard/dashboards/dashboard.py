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
    def convert_image_size_units(units, dpi, width, height, prev_units, prev_dpi):
        if prev_dpi != dpi and units == 'px':
            width *= dpi / prev_dpi
            height *= dpi / prev_dpi
        else:
            if units == 'in':
                if prev_units == 'cm':
                    width /= 2.54
                    height /= 2.54
                if prev_units == 'px':
                    width /= dpi
                    height /= dpi
            if units == 'cm':
                if prev_units == 'in':
                    width *= 2.54
                    height *= 2.54
                if prev_units == 'px':
                    width *= 2.54 / dpi
                    height *= 2.54 / dpi
            if units == 'px':
                if prev_units == 'in':
                    width *= dpi
                    height *= dpi
                if prev_units == 'cm':
                    width *= 2.54 * dpi
                    height *= 2.54 * dpi
        return width, height, units, dpi

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
                <link rel="stylesheet" href="https://use.fontawesome.com/releases/v5.7.0/css/all.css" integrity="sha384-lZN37f5QGtY3VHgisS14W3ExzMWZxybE1SJSEsQp9S+oqd12jhcu+A56Ebc1zFSJ" crossorigin="anonymous">
                <title>{kwargs["title"]}</title>
            </head>
            <body>
                {kwargs["app_entry"]}
                {kwargs["config"]}
                {kwargs["scripts"]}
                <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.3.1/jquery.min.js" integrity="sha256-FgpCb/KJQlLNfOu91ta32o/NMZxltwRo8QtmkMRdAu8=" crossorigin="anonymous"></script>
                <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.2.1/js/bootstrap.bundle.min.js" integrity="sha384-zDnhMsjVZfS3hiP7oCBRmfjkQC4fzxVxFhBx8Hkz2aZX8gEvA/jsP3eXRCvzTofP" crossorigin="anonymous"></script>
                {kwargs["renderer"]}
            </body>
        </html>
        '''


def get_plot_theme():
    try:
        return 'plotly_dark' if current_user and current_user.theme == 'dark' else 'plotly_white'
    except:
        return 'plotly_white'
