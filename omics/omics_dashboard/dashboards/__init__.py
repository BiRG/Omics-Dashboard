"""
You can append packages to this to integrate other dashboards.
You need a factory class that inherits Dashboard. The only method called is the factory method create_dash_app.
The methods should all be static.
We have to use the factory pattern because the flask app has to be initialized before any of the dashboards are initialized
"""
from typing import List, Type

from dashboards.dashboard import Dashboard
from dashboards.nmr_metabolomics.opls import OPLSDashboard
from dashboards.nmr_metabolomics.pca import PCADashboard
from dashboards.nmr_metabolomics.visualization import VisualizationDashboard
from dashboards.nmr_metabolomics.collection_editor import CollectionEditorDashboard
from dashboards.nmr_metabolomics.processing import CollectionProcessingDashboard

dashboard_list: List[Type[Dashboard]] = [
    VisualizationDashboard,
    CollectionEditorDashboard,
    CollectionProcessingDashboard,
    PCADashboard,
    OPLSDashboard,
]
