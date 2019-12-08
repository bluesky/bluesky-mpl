import collections

from event_model import DocumentRouter
import matplotlib.pyplot as plt
import numpy


class Line(DocumentRouter):
    """
    Draw a matplotlib Line Arist update it for each Event.

    Parameters
    ----------
    func : callable
        This must accept an EventPage and return two lists of floats
        (x points and y points). The two lists must contain an equal number of
        items, but that number is arbitrary. That is, a given document may add
        one new point to the plot, no new points, or multiple new points.
    label_template : string, optional
        This string will be formatted with the RunStart document. Any missing
        values will be filled with '?'. If the keyword argument 'label' is
        given, this argument will be ignored.
    ax : matplotlib Axes, optional
        If None, a new Figure and Axes are created.
    **kwargs
        Passed through to :meth:`Axes.plot` to style Line object.
    """
    def __init__(self, func, *, label_template='{scan_id} [{uid:.8}]', ax=None, **kwargs):
        self.func = func
        if ax is None:
            _, ax = plt.subplots()
        self.ax = ax
        self.line, = ax.plot([], [], **kwargs)
        self.x_data = []
        self.y_data = []
        self.label_template = label_template
        self.label = kwargs.get('label')

    @classmethod
    def from_expr(cls, x, y, *, label_template='{scan_id} [{uid:.8}]', ax=None, **kwargs):
        """
        Construct a Line from expressions given as strings.

        The strings can be fields names, 'time', 'seq_num', or mathematical
        functions thereof. All functions in the numpy namespace are available.
        See examples below.

        Parameters
        ----------
        x: string
        y: string
        label_template : string, optional
            This string will be formatted with the RunStart document. Any missing
            values will be filled with '?'. If the keyword argument 'label' is
            given, this argument will be ignored.
        ax : matplotlib Axes, optional
            If None, a new Figure and Axes are created.
        **kwargs
            Passed through to :meth:`Axes.plot` to style Line object.

        Examples
        --------
        Plot intensity 'I' vs temperature 'T'.

        >>> line = Line.from_expr('T', 'I')

        Plot intensity 'I' vs Event time.

        >>> line = Line.from_expr('time', 'I')

        Plot intensity 'I' normalized by 'I0' vs Event sequence number.

        >>> line = Line.from_expr('seq_num', 'I/I0')

        Plot the log(I/I0) vs Event time. This uses numpy.log. Any numpy
        function is available.

        >>> line = Line.from_expr('seq_num', 'log(I/I0)')
        """
        def func(event_page):
            namespace = dict(collections.ChainMap(
                {k: numpy.asarray(v) for k, v in event_page['data'].items()},
                event_page,
                numpy.__dict__))
            return eval(x, namespace), eval(y, namespace)
        return cls(func, label_template=label_template, ax=ax, **kwargs)

    def start(self, doc):
        if self.label is None:
            d = collections.defaultdict(lambda: '?')
            d.update(**doc)
            label = self.label_template.format_map(d)
        else:
            label = self.label
        if label:
            self.line.set_label(label)
            self.ax.legend(loc='best')

    def event_page(self, doc):
        x, y = self.func(doc)
        self._update(x, y)

    def _update(self, x, y):
        """
        Takes in new x and y points and redraws plot if they are not empty.
        """
        if not len(x) == len(y):
            raise ValueError("User function is expected to provide the same "
                             "number of x and y points. Got {len(x)} x points "
                             "and {len(y)} y points.")
        if not x:
            # No new data. Short-circuit.
            return
        self.x_data.extend(x)
        self.y_data.extend(y)
        self.line.set_data(self.x_data, self.y_data)
        self.ax.relim(visible_only=True)
        self.ax.autoscale_view(tight=True)
        self.ax.figure.canvas.draw_idle()
