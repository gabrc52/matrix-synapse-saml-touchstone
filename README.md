# Synapse Touchstone SAML MXID Mapper

A Synapse plugin module which allows users to choose their display name when they
first log in.

## Installation

```
pip install .
```

### Config

Add the following in your Synapse config:

```yaml
   saml2_config:
     user_mapping_provider:
       module: "matrix_synapse_saml_touchstone.SamlMappingProvider"
```

Also, under the HTTP client `listener`, configure an `additional_resource` as per
the below:

```yaml
listeners:
  - port: <port>
    type: http

    resources:
      - names: [client]

    additional_resources:
      "/_matrix/saml2/pick_displayname":
        module: "matrix_synapse_saml_touchstone.pick_displayname_resource"
```

### Configuration Options

Synapse allows SAML mapping providers to specify custom configuration through the
`saml2_config.user_mapping_provider.config` option.

There are no configuration options supported at the moment.

## Implementation notes

The login flow looks something like this:

![login flow](https://raw.githubusercontent.com/matrix-org/matrix-synapse-saml-mozilla/master/doc/login_flow.svg?sanitize=true)

## Development and Testing

This repository uses `tox` to run linting and tests.

### Linting

Code is linted with the `flake8` tool. Run `tox -e lint` to check for linting
errors in the codebase.

### Tests

This repository uses `unittest` to run the tests located in the `tests`
directory. They can be ran with `tox -e tests`.

### Making a release

```
git tag vX.Y
python3 setup.py sdist
twine upload dist/matrix-synapse-saml-mozilla-X.Y.tar.gz
git push origin vX.Y
```
