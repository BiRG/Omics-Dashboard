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
