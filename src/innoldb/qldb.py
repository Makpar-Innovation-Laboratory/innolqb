import uuid
from botocore.exceptions import ClientError
from itertools import tee
from innoldb import settings
from innoldb.static.logger import getLogger
from innoldb.static.driver import Driver
from innoldb.static.objects import Strut

log = getLogger('innoldb.qldb')


class QLDB():
    """A class containing meta information associated with QLDB ledger.
    """

    def __init__(self, table, ledger=settings.LEDGER):
        """Creates an instance of `qldb-orm.qldb.QLDB`. This class representation some basic configuration properties of the **QLDB** ledger.

        :param table: Name of the table onto which transactions will read and write.
        :type table: str
        :param ledger: Name of the ledger where tables are stored, defaults to `qldb-orm.settings.LEDGER`
        :type ledger: str, optional
        """
        self.table = table
        self.ledger = ledger
        self.index = 'id'


class Document(QLDB):
    """A `qldb-orm.qldb.Document` object, representing an entry in an QLDB Ledger Table. Creates an instance of `qldb-orm.qldb.Document`. This object can be initialized in several states, depending on the parameters passed into the constructor.

    1. **Constructor Arguments**: `table`
    2. **Constructor Arguments**: `table, id`
    3. **Constructor Arguments**: `table, snapshot`

    In each case, an optional argument for `ledger` and `stranded` can be passed in. 

    :param table: Name of the **QLDB**table
    :type table: str
    :param id: Id of the document to load, defaults to `None`
    :type id: str, optional
    :param snapshot: `dict` containing values to map to attributes, defaults to `None`
    :type snapshot: dict, optional
    :param ledger: Name of the **QLDB** ledger, defaults to `qldb-orm.settings.LEDGER`
    :type ledger: str, optional
    :param stranded: Flag to signal the document should initialized its history from the **QLDB** ledger

    .. note::
      If `stranded==True`, then the document history can be accessed through `self.strands`
    """

    def __init__(self, table, id=None, snapshot=None, ledger=settings.LEDGER, stranded=False):
        super().__init__(table=table, ledger=ledger)

        self.meta_id = None

        if id is None:
            # PartiQL doesn't like dashes.
            self.id = str(uuid.uuid1()).replace('-', '')
            if snapshot is not None:
                self._load(snapshot)

        elif id is not None:
            self.id = id
            if snapshot is None:
                self._exists(self.id, snapshot=True)
            else:
                self._load(snapshot)

        self._init_fixtures()

        if stranded and self.meta_id is not None:
            self._init_history()

    def __getattr__(self, attr):
        """Return values from un-hidden fields. Hidden fields include: `index`, `table`, `ledger`.

        :param attr: attribute key
        :type attr: str
        """
        return self.fields().get(attr, None)

    def _init_fixtures(self):
        """Create the table and index on the **QLDB** ledger, if they do not already exist.
        """
        if self.table not in Driver.tables(self.ledger):
            try:
                Driver.create_table(Driver.driver(self.ledger), self.table)
                Driver.create_index(Driver.driver(
                    self.ledger), self.table, self.index)
            except ClientError as e:
                log.error(e)

    def _init_history(self):
        """Initializes the `qldb-orm.qldb.Document` revision history. After this method is invoked, the `self.strands` attribute will be populated with an array of `qldb-orm.qldb.Document` ordered over the revision history from earliest to latest.
        """
        self.strands = []
        history = Query(self.table).history(self.meta_id)
        for doc in history:
            self.strands.append(
                Document(self.table, id=self.id, snapshot=doc.data))

    def _load(self, snapshot=None, nest=None, nester=None):
        """Parse the `snapshot` into `qldb-orm.qldb.Document` attributes. If `nest` and `nester` are passed in, the function executes recursively, drilling down through the nodes in the `snapshot` and recursively generating the document structure.

        :param snapshot: `dict` of attributes to append to self, defaults to `None`
        :type snapshot: dict, optional
        :param nest: Key of the nested field in the document attribute path.
        :type nest: str
        :param nester: Nested field, defaults to `None`.
        :type nester: :class:`Strut`, optional

        .. note::
          1. https://realpython.com/python-eval-function/
          2. https://blog.sqreen.com/preventing-sql-injections-in-python/
          3. https://nedbatchelder.com/blog/201206/eval_really_is_dangerous.html
        """
        if snapshot is not None:
            if isinstance(snapshot, Strut):
                snapshot = vars(snapshot)

            for key, value in snapshot.items():

                if isinstance(value, dict):
                    nested_field = Strut()

                    if nest is None:
                        setattr(self, key, nested_field)
                        nested_key = f'self.{key}'
                        self._load(snapshot=value, nest=nested_key,
                                   nester=nested_field)

                    else:
                        path = '.'.join(nest.split('.')[:-1])
                        nest_endpoint = nest.split('.')[-1]
                        # NOTE: see links in docstring for comments on the use of `eval()`
                        nested_attribute = getattr(
                            eval(path, {'__builtins__': {}, "self": self}), nest_endpoint)
                        setattr(nested_attribute, key, nested_field)
                        nested_key = f'{nest}.{key}'
                        self._load(snapshot=value, nest=nested_key,
                                   nester=nested_field)

                else:
                    if nest is None:
                        setattr(self, key, value)

                    else:
                        setattr(nester, key, value)

    def _insert(self, document):
        """Insert a new `innoldab.qldb.Document` into the **QLDB** ledger table.

        :param document: `dict` containing the fields to be inserted.
        :type document: dict
        :return: `dict` containing `INSERT` response
        :rtype: dict
        """
        log.debug("Inserting DOCUMENT(%s = %s)",
                  self.index, document[self.index])
        return dict(next(Driver.insert(Driver.driver(self.ledger), document, self.table), None))

    def _update(self, document):
        """Update an existing `innoldab.qldb.Document` on the **QLDB** ledger table.

        :param document: Dictionary containing the fields to be updated.
        :type document: dict
        :return: Dictionary containg `UPDATE` response
        :rtype: dict
        """
        log.debug("Updating DOCUMENT(%s = %s)",
                  self.index, document[self.index])
        return dict(next(Driver.update(Driver.driver(self.ledger), document, self.table, self.index), None))

    def _get(self, id):
        """Retrieve an existing `innoldab.qldb.Document` from the **QLDB** ledger table.

        :param id: ID of the `innoldab.qldb.Document` to retrieve
        :type id: str
        :return: Dictionary containing the `SELECT` response
        :rtype: dict
        """
        log.debug("Returning DOCUMENT(%s = %s)", self.index, id)
        return dict(next(Driver.query_by_fields(Driver.driver(self.ledger), self.table, **{self.index: id}), None))

    def _exists(self, id, snapshot=False):
        """Check if a `qldb-orm.qldb.Document` exists in the **QLDB** ledger table.

        :param id: ID of the `qldb-orm.qldb.Document` whose existence is in question.
        :type id: str
        :param snapshot: Flag to persist values retrieved from existence query to object, defaults to False.
        :type snapshot: bool
        :return: True if exists, False otherwise
        :rtype: bool
        """
        log.debug("Checking existence of DOCUMENT(%s = %s)", self.index, id)
        result = Driver.query_by_fields(Driver.driver(
            self.ledger), self.table, **{self.index: id})
        first_it, second_it = tee(result)
        if next(first_it, None):
            if snapshot:
                self._load(dict(next(second_it, None)))
            return True
        return False

    def fields(self):
        """All of the `qldb-orm.qldb.Document` fields as a key-value `dict`. Hides the document attributes `table`, `driver`, `index` and `ledger`, if an object containing only the relevant fields.

        :return: `qldb-orm.qldb.Document` fields
        :rtype: dict
        """
        return {key: value for key, value in vars(self).items() if key not in ['table', 'driver', 'index', 'ledger', 'meta_id', 'strands']}

    def save(self):
        """Save the current value of the `qldb-orm.qldb.Document` fields to the **QLDB** ledger table.
        """
        fields = self.fields()
        log.debug("Saving DOCUMENT(%s = %s)", self.index, fields[self.index])
        if self._exists(fields[self.index]):
            result = self._update(fields)
        else:
            result = self._insert(fields)
        self.meta_id = result['documentId']
        if self.stranded:
            self._init_history()


class Query(QLDB):
    """Object that represents a **PartiQL** query. Get initialized on a particular `table` and `ledger`.

    Methods will return results formatted as collections of `qldb-orm.qldb.Document`.
    """

    def __init__(self, table, ledger=settings.LEDGER):
        super().__init__(table=table, ledger=ledger)

    def _to_documents(self, results):
        """Convert query results to a `list` of `qldb-orm.qldb.Document`

        :param results: Result of `pyqldb` cursor execution
        :return: collection of documents
        :rtype: list
        """
        return [Document(table=self.table, snapshot=dict(result)) for result in results]

    def raw(self, query):
        """Execute a raw query against the **QLDB** ledger.

        :param query: Query to be executed
        :type query: str
        :return: a collection of `qldb-orm.qldb.Document`
        :rtype: list

        .. warning::
          Query will not be sanitized for injections.
        """
        return self._to_documents(Driver.query(Driver.driver(self.ledger), query, unsafe=True))

    def history(self, id=None):
        """Returns the revision history.

        :param id: meta id, defaults to None
        :type id: id of the document revision history , optional
        :return: a collection of `qldb-orm.qldb.Document`
        :rtype: list
        .. note::
          `id` is *not* the index of the document. It is the `metadata.id` associated with the document across revisions. Query entire history to find a particular `metadata.id`
        """
        if id is None:
            records = [Driver.down_convert(record)
                       for record in Driver.history_full(Driver.driver(self.ledger), self.table)]
        else:
            records = [Driver.down_convert(record)
                       for record in Driver.history(Driver.driver(self.ledger), self.table, id)]

        return self._to_documents(records)

    def get_all(self):
        """Return all `qldb-orm.qldb.Document` objects in the **QLDB** ledger table

        :return: List of `qldb-orm.qldb.Document`
        :rtype: list
        """
        return self._to_documents(Driver.query_all(Driver.driver(self.ledger), self.table))

    def find_by(self, **kwargs):
        """Filter `qldb-orm.qldb.Document` objects by the provided fields. This method accepts `**kwargs` arguments for the field name and values. The document fields must exactly match the fields provided in the query.

        :param kwargs: Fields by which to filter the query.
        :return: List of `qldb-orm.qldb.Document`
        :rtype: list
        """
        return self._to_documents(Driver.query_by_fields(Driver.driver(self.ledger), self.table, **kwargs))

    def find_in(self, **kwargs):
        """Filter `qldb-orm.qldb.Document` objects by the provided fields. This method accepts `**kwargs` arguments for the field name and values, but the values must be an array. 

        The document fields must belong to the array associated with the field in the `**kwargs`. See below for example.

        :param kwargs: Fields by which to filter the query.
        :return: List of `qldb-orm.qldb.Document`
        :rtype: list

        .. note:: Example
            ```python
            Query('table').find_in(**{'field': [12, 13, 14], 'field2': ['cat', 'dog' ]})
            ```
            will find all documents with a `field` whose value is in the set `(12, 13, 14)` *and* a `field2` whose value is in the set `('cat', 'dog')`
        """
        return self._to_documents(Driver.query_in_fields(Driver.driver(self.ledger), self.table, **kwargs))
