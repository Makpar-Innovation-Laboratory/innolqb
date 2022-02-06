# Makpar Innovation Lab

## innoldb

A simple [Object-Relation-Mapping](https://en.wikipedia.org/wiki/Object%E2%80%93relational_mapping) for a serverless [AWS Quantum Ledger Database](https://docs.aws.amazon.com/qldb/latest/developerguide/what-is.html) backend, and a command line utility for querying tables on those ledgers.

**NOTE**: The user or process using this library must have an [IAM policy that allows access to QLDB](https://docs.aws.amazon.com/qldb/latest/developerguide/security-iam.html).


```python
from innoldb.qldb import Document

document = Document('my-table')
document.field = 'my field'
document.save()
```

## Setup
### Overview
1. (Optional) Configure environment
2. Create **QLDB** Ledger
3. Configure IAM user/role permissions for ledger
4. Install library

### Steps

1. (Optional) Configure Environment

This library needs to be informed of the QLDB Ledger to write against on your AWS environment. There are several ways to configure the Ledger setting. 

Before you start a Python shell, export the**LEDGER** environment variable,

```shell
export LEDGER='ledger-name'
python
```

Alternatively, configure the variable directly in a Python script

```python
import os

os.environ['LEDGER'] = 'ledger=name'
```

The environment variable **LEDGER** should point to the **QLDB** ledger so the application knows to which ledger to write. If you do not configure the **LEDGER** environment variable, you will need to pass in the ledger name to the `Document` object. See [below](#documents) for more information.

2. Create a **QLDB** Ledger

Boto3 Client
------------

The easiest way to create a ledger is through the `boto3` wrapper function in `innoldb.qldb.Driver`,

```python
from innoldb.qldb import Driver

Driver.ledger('my-ledger')
```

**NOTE**: You must install the `innoldb` package from [PyPi](https://pypi.org/project/innoldb/) before creating a ledger this way. See *Step 4* for more information.

CloudFormation
--------------

A **QLDB** CloudFormation template is also available in the *cf* directory of this project's [Github](https://github.com/Makpar-Innovation-Laboratory/innoldb). A script has been provided to post this template to **CloudFormation**, assuming your [AWS CLI has been authenticated and configured](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html). Clone the repository and then from the project root, execute the following script and specify the `<ledger-name>` to create a ledger on the **QLDB** service,

```shell
./scripts/cf-stack --ledger <ledger-name>
```

**NOTE**: The `<ledger-name>` must match the value of the **LEDGER** environment variable. The name of the ledger that is stood up on AWS is passed to the library through this environment variable.

**NOTE**: This script has other optional arguments detailed in the comments of the script itself.

3. Configure User Permissions

In production, you will want to limit the permissions of the application client to the ledger and table to which it is authorized to read and write. For the purposes of using this library locally, you can add a blanket policy to your user account by [following the instructions here](https://docs.aws.amazon.com/qldb/latest/developerguide/getting-started.prereqs.html#getting-started.prereqs.permissions).

If you are configuring an application role to use this library for a particular ledger and table, you will need to scope the permissions using [this reference](https://docs.aws.amazon.com/qldb/latest/developerguide/getting-started-standard-mode.html).

4. Install `innoldb`

```shell
pip install innoldb
```

## Command Line Usage

Installing the `innoldb` package puts a command line utility on your path. This tool allows you to query the QLDB ledger directly from the command line. 

The `--table` argument is required. Queries can be constructed against this table by passing in other arguments. See below for examples of the different queries.

Be sure to export the **LEDGER** environment variable before executing any of these commands,

```shell
export LEDGER='ledger-name'
```

### Find Document By ID

```shell
innoldb --table <table-name> --id <id>
```

### Find All Documents

```shell
innoldb --table <table-name> --all
```

### Generate New Mock Document

```shell
innoldb --table <table-name> --mock
```

### Update Field in Document

```shell
innoldb --table <table-name> --id <id> --update <field>=<value> <field>=<value> ...
```

### Insert Document

```shell
innoldb --table <table-name> --insert <field>=<value> <field>=<value> ...
```

## Document Object Model

This library abstracts much of the QLDB implementation away from its user. All the user has to do is create a `Document` object, add fields to it and then call `save()`. Under the hood, the library will translate the `Document` fields into [PartiQL queries](https://partiql.org/docs.html) and use the [pyqldb Driver](https://amazon-qldb-driver-python.readthedocs.io/en/stable/index.html) to post the queries to the **QLDB** instance on AWS.

**NOTE**: All documents are indexed through the key field `id`. 

### Saving

If you have the **LEDGER** environment variable set, all that is required is to create a `Document` object and pass it the table name from the **QLDB** ledger. If the following lines are feed into an interactive **Python** shell or copied into a script,

```python
from innoldb.qldb import Document

my_document = Document('table-name')
my_document.property_one = 'property 1'
my_document.property_two = 'property 2'
my_document.save()
```

Then a document will be inserted into the **QLDB** ledger table. If you do not have the **LEDGER** environment variable set, you must pass in the ledger name along with the table name through named arguments,

```python
from innoldb.qldb import Document

my_document = Document(table='table-name', ledger='ledger-name')
my_document.property_one = 'property 1'
my_document.property_two = 'property 2'
my_document.save()
```

**NOTE**: The `Document` class will auto-generate a UUID for each document inserted into the ledger table. 

Congratulations! You have saved a document to QLDB!

### Loading

To load a document that exists in the ledger table already, pass in the id of the `Document` when creating a new instance,

```python
from innoldb.qldb import Document

my_document(table='table-name', id='12345')
print(my_document.property_one)
```

### Updating

Updating and saving are different operations, in terms of the **PartiQL** queries that implement these operations, but from the `Document`'s perspective, they are the same operation; the same method is called in either case. The following script will save a value of `test 1` to `field` and then overwrite it with a value of `test 2`,

```python
from innoldb.qldb import Document

my_document = Document('table-name')
my_document.field = 'test 1'
my_document.save()
my_document.field = 'test 2'
my_document.save()
```

Behind the scenes, whenever the `save()` method is called, a query is run to check for the existence of the given `Document`. If the `Document` doesn't exist, the library will create a new one. If the `Document` does exist, the library will overwrite the existing `Document`.

### Fields

The document fields can be returned as a `dict` through the `fields()` method. The following script will loop through the fields on an existing document with `id=test` and print their corresponding values,

```python
from innoldb.qldb import Document

my_document = Document(table='table-name', id='test')

for key, value in my_document.fields().items():
  print(key, '=', value)
```

## Query Object Model

Queries are represented as an object, `Query`. Each `Query` must be initialized with a `table` that it will run **PartialQL** queries against. All queries return a `list` of `Document` objects. 

### All

The following script queries the ledger table for all documents and prints a JSON representation of each document to screen,

```python
from innoldb.qldb import Document, Query

all_documents = Query('table-name').all()
for document in all_documents:
  print(document.fields())
```

## Configuration

### Log Level

The log level can be set through the environment variable **LOG_LEVEL** to the values: `NOTSET`, `INFO`, `DEBUG` and `ERROR`,

```shell
export LOG_LEVEL='INFO'
innoldb --table table-name --all
```

```python
import os
from innoldb.qldb import Query

os.environ['LOG_LEVEL'] = 'DEBUG'
Query('table-name').all()
```

## Build From Source

The `innoldb` library can be built from source with the following script,

```shell
git clone https://github.com/Makpar-Innovation-Laboratory/innoldb
cd innoldb
python -m build
VERSION=$(cat version.txt)
cd dist
pip install innoldb-${VERSION}-py3-none-any.whl
```

Or use the pre-packaged helper script,

```shell
git clone https://github.com/Makpar-Innovation-Laboratory/innoldb
./innoldb/scripts/install
```

## References 
- [AWS QLDB Documentation](https://docs.aws.amazon.com/qldb/latest/developerguide/what-is.html)
- [QLDB Python Driver Documentation](https://amazon-qldb-driver-python.readthedocs.io/en/stable/index.html)
- [Boto3 QLDB Client Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/qldb.html)
- [PartiQL Documentation](https://partiql.org/docs.html)