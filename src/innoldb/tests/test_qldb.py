import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(TEST_DIR)
sys.path.append(APP_DIR)

import pytest
from unittest.mock import patch
from qldb import Document, Strut, Ledger

@pytest.mark.parametrize('kwargs,keys,values',[
  ({'a':'b'},['a'], ['b']),
  ({'dog': 'woof', 'cat': 'meow', 'whale': 'waa'}, ['dog', 'cat', 'whale'], ['woof', 'meow', 'waa'])
])
def test_strut(kwargs,keys,values):
  keywords = vars(Strut(**kwargs))
  assert all(keywords[act_key] == exp_val for act_key, exp_key, exp_val in zip(keywords.keys(), keys, values))

@pytest.mark.parametrize('table,ledger',[
  ('howdy','ho'),
  ('alas', 'poor yorick'),
  ('say what', 'again')
])
def test_ledger(table, ledger):
  assert Ledger(table, ledger).table == table and Ledger(table, ledger).ledger == ledger

@patch('qldb.Driver.driver')
@patch('qldb.Driver.tables')
@patch('qldb.Driver.create_table')
@patch('qldb.Driver.create_index')
def test_document_driver(mock_create_index, mock_create_table, mock_tables, mock_driver):
  Document(table='table', ledger='ledger')
  assert mock_driver.called
  assert mock_tables.called
  assert mock_create_table.called
  assert mock_create_index.called
