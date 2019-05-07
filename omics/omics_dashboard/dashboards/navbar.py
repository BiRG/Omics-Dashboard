import os

import dash_bootstrap_components as dbc
import dash_html_components as html
from flask_login import current_user


def get_navbar():
    from . import dashboard_list
    brand = os.environ['BRAND'] if 'BRAND' in os.environ else ''
    try:
        user_name = current_user.name
    except:
        user_name = '<Current User>'

    root_url = '/omics/'
    logout_url = root_url + 'logout'
    dashboard_url = root_url + 'dashboards'

    return dbc.NavbarSimple(
        [
            dbc.DropdownMenu(
                [
                    dbc.DropdownMenuItem(dashboard.name, href=root_url + dashboard.prefix[1:], external_link=True)
                    for dashboard in dashboard_list
                ], nav=True, label='Dashboards', in_navbar=True
            ),
            dbc.DropdownMenu(
                [
                    dbc.DropdownMenuItem([html.I(className='fas fa-sign-out-alt'), ' Logout'], href=logout_url,
                                         external_link=True)
                ], nav=True, in_navbar=True, label=user_name
            )
        ],
        brand=f'Omics Dashboard @ {brand}',
        brand_href=dashboard_url,
        brand_external_link=True,
        color='primary',
        dark=True
    )
