from flask import request, render_template, redirect, url_for, Blueprint

from data_tools.template_data.entry_page import SamplePageData
from data_tools.template_data.list_table import ListTableData
from data_tools.samples import get_samples, get_sample, update_sample, delete_sample
from helpers import get_current_user, handle_exception_browser

samples = Blueprint('samples', __name__, url_prefix='/samples')


@samples.route('/', methods=['GET', 'POST'])
def render_sample_list():
    try:
        current_user = get_current_user()
        return render_template('pages/list.html',
                               page_data=ListTableData(current_user, get_samples(current_user), 'Samples'))
    except Exception as e:
        return handle_exception_browser(e)


@samples.route('/<sample_id>', methods=['GET', 'POST', 'DELETE'])
def render_sample(sample_id=None):
    try:
        current_user = get_current_user()
        sample = get_sample(current_user, sample_id)
        if request.method == 'DELETE':
            delete_sample(current_user, sample)
            return redirect(url_for('samples.render_sample_list'))
        if request.method == 'POST':
            update_sample(current_user, sample, request.form)
        return render_template('pages/sample_entry.html',
                               page_data=SamplePageData(current_user, sample))
    except Exception as e:
        return handle_exception_browser(e)


