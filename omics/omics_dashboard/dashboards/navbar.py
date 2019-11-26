import dash_html_components as html
from flask_login import current_user
import os
from flask import url_for
from jinja2 import Template
import dash_dangerously_set_inner_html
from pathlib import Path

brand = os.environ['BRAND'] if 'BRAND' in os.environ else ''


def url_for_(endpoint, **values):
    try:
        return url_for(endpoint, **values)
    except RuntimeError:
        return ''


def get_navbar():
    navbar_template = Path(__file__).parent.parent.joinpath('templates/components/navbar.html')
    navbar_html = Template(navbar_template.open().read()).render(url_for=url_for_,
                                                                 current_user=current_user, BRAND=brand)
    return html.Div(dash_dangerously_set_inner_html.DangerouslySetInnerHTML(navbar_html))

