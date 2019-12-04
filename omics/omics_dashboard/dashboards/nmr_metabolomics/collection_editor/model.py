from dashboards.dashboard_model import DashboardModel


class CollectionEditorModel(DashboardModel):
    _redis_prefix = 'collection_editor'
    _empty_plot_data = {}

