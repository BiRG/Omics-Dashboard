import re

import dash_html_components as html
import dash_table
import pandas as pd
from flask_login import current_user
from plotly import graph_objs as go
from plotly.colors import DEFAULT_PLOTLY_COLORS

from dashboards.dashboard_model import DashboardModel
from data_tools.access_wrappers.collections import get_collection


class VisualizationModel(DashboardModel):
    _redis_prefix = 'viz'
    _empty_plot_data = {}

    def get_plot(self, queries, group_by, labels, theme, bin_collection_id, legend_style, background_color):
        print(background_color)
        labels = labels or []
        self.load_dataframes()
        if bin_collection_id is not None:
            print(bin_collection_id)
            bin_collection = get_collection(current_user, bin_collection_id)
            x_mins = bin_collection.get_dataset('x_min').ravel().tolist()
            x_maxes = bin_collection.get_dataset('x_max').ravel().tolist()
            colors = [DEFAULT_PLOTLY_COLORS[i % 2] for i in range(len(x_mins))]
            shapes = [
                go.layout.Shape(
                    type='rect',
                    xref='x',
                    yref='paper',
                    x0=x_min,
                    y0=0,
                    x1=x_max,
                    y1=1,
                    fillcolor=color,
                    opacity=0.2,
                    layer='below',
                    line_width=0
                )
                for x_min, x_max, color in zip(x_mins, x_maxes, colors)
            ]
        else:
            shapes = []

        axis_line_style = {
            'zerolinecolor': '#375A7F',  # darkly primary
            'gridcolor': '#444444'  # darkly secondary
        } if theme == 'plotly_dark' and background_color != 'rgba(255,255,255,1)' else {
            'zerolinecolor': '#2C3E50',  # flatly primary
            'gridcolor': '#95A5A6'  # flatly secondary
        }
        if legend_style in ('full', 'groups'):
            layout = go.Layout(
                height=700,
                font={'size': 16},
                margin={'t': 25, 'l': 25, 'b': 25, 'r': 25},
                template=theme,
                plot_bgcolor=background_color,
                paper_bgcolor=background_color,
                xaxis={
                    'title': 'Chemical Shift (ppm)',
                    'autorange': 'reversed',
                    **axis_line_style
                },
                yaxis={
                    'title': 'Intensity',
                    **axis_line_style
                },
                shapes=shapes
            )
        else:  # if legend_style == 'none'
            layout = go.Layout(
                height=700,
                font={'size': 16},
                margin={'t': 25, 'l': 25, 'b': 25, 'r': 25},
                template=theme,
                plot_bgcolor=background_color,
                paper_bgcolor=background_color,
                xaxis={
                    'title': 'Chemical Shift (ppm)',
                    'autorange': 'reversed',
                    **axis_line_style
                },
                yaxis={
                    'title': 'Intensity',
                    **axis_line_style
                },
                shapes=shapes,
                showlegend=False
            )

        color_indices = [self._label_df.query(query).index for query in queries]
        if len(color_indices) > len(DEFAULT_PLOTLY_COLORS):  # repeat default color list
            colors = []
            while len(colors) < len(color_indices):
                colors += DEFAULT_PLOTLY_COLORS
        else:
            colors = DEFAULT_PLOTLY_COLORS
        colors = colors[:len(color_indices)]
        x = self._numeric_df.columns.values.astype(float)
        figure = go.Figure(layout=layout)

        if legend_style == 'full' or legend_style == 'groups':
            figure.add_trace(
                go.Scatter(  # dummy series to use as stand-in for legend title
                    x=[0],
                    y=[0],
                    name=','.join(group_by),
                    mode='markers',
                    marker={
                        'opacity': 0,
                        'size': 0,
                        'color': 'rgba(0,0,0,0)'
                    }
                )
            )

            for query, color in zip(queries, colors):
                # split query
                figure.add_trace(
                    go.Scatter(  # dummy series to label colors
                        x=[0],
                        y=[0],
                        name=','.join(re.findall(r'["](\w+)["]', query)),  # pretty kludgy
                        mode='lines',
                        marker={'color': color},
                        legendgroup=query
                    )
                )

            figure.add_trace(
                go.Scatter(  # dummy series to provide space between color key and "heading"
                    x=[0],
                    y=[0],
                    name='',
                    mode='markers',
                    marker={
                        'opacity': 0,
                        'size': 0,
                        'color': 'rgba(0,0,0,0)'
                    }
                )
            )

        if legend_style == 'full':
            figure.add_trace(
                go.Scatter(  # dummy series to use as stand-in for legend title
                    x=[0],
                    y=[0],
                    name=f"({', '.join(labels)})" if len(labels) else 'Spectrum #',
                    mode='markers',
                    marker={
                        'opacity': 0,
                        'size': 0,
                        'color': 'rgba(0,0,0,0)'
                    }
                )
            )

        for query, color in zip(queries, colors):
            y_values = self._numeric_df.loc[self._label_df.query(query).index]
            for i, row in y_values.iterrows():
                text = '<br>'.join([f'{label}=={self._label_df.loc[i][label]}' for label in self._label_df.columns])
                if len(labels):
                    name = f"({', '.join([f'{self._label_df.loc[i][label]}' for label in labels])})"
                else:
                    name = f'({i})'
                if legend_style == 'groups':
                    figure.add_trace(
                        go.Scatter(
                            x=x,
                            y=row,
                            text=text,
                            name=','.join(re.findall(r'["](\w+)["]', query)),  # pretty kludgy
                            mode='lines',
                            marker={'color': color, 'size': 1},
                            legendgroup=query,
                            showlegend=False
                        )
                    )
                else:
                    figure.add_trace(
                        go.Scatter(
                            x=x,
                            y=row,
                            text=text,
                            name=name,
                            mode='lines',
                            marker={'color': color, 'size': 2},
                            showlegend=(legend_style == 'full')
                        )
                    )

        return figure

    def get_summary(self, queries, labels, x_min, x_max, theme):
        labels = labels or []
        self.load_dataframes()
        in_range_columns = [column for column in self._numeric_df.columns if x_min <= float(column) <= x_max]
        # find sum of points in range
        # average and median sum
        results_dfs = []
        label_column = f'({", ".join(labels)})'
        for query in queries:
            results_df = pd.DataFrame()
            sub_label_df = self._label_df.query(query)
            sub_numeric_df = self._numeric_df.loc[sub_label_df.index]
            sums = sub_numeric_df[in_range_columns].sum(axis=1)
            results_df[label_column] = sub_label_df.apply(
                lambda row: f'({",".join([str(row[label]) for label in labels])})', axis=1)
            results_df['Sum'] = sums
            summary_df = pd.DataFrame()
            summary_df[label_column] = [f'Average({query})', f'Median({query})']
            summary_df['Sum'] = [sums.mean(), sums.median()]
            results_df = summary_df.append(results_df)
            results_dfs.append(results_df)
        style_header = {'backgroundColor': '#303030'} if theme == 'plotly_dark' else {}
        style_cell = {'backgroundColor': '#444444'} if theme == 'plotly_dark' else {}

        return [item for pair in [
            (html.H5(query),
             dash_table.DataTable(columns=[{'name': val, 'id': val} for val in df.columns],
                                  data=df.to_dict('rows'),
                                  style_header=style_header,
                                  style_cell=style_cell,
                                  style_data_conditional=[
                                      {
                                          'if': {'row_index': 0},
                                          'fontStyle': 'italic'
                                      },
                                      {
                                          'if': {'row_index': 1},
                                          'fontStyle': 'italic'
                                      }
                                  ]),
             html.Br()
             )
            for query, df in zip(queries, results_dfs)
        ] for item in pair]
