# Dashboard Expansions
You can add any [Dash](https://dash.plot.ly/) application as a dashboard, so long as you create a wrapper that inherits 
the `Dashboard` class defined in `dashboard.py` and initializes the app in the `create_dash_app` method. Your Dash 
applications should inherit `StyledDash` to match the theming of Omics Dashboard. Your applications become integrated 
with the backend and have full access to the Omics Dashboard system.

To include a common navbar with a list of available dashboards and a link back to Omics Dashboard, your layout method 
should call `get_navbar()` from `navbar.py`.