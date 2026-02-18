When preparing to release to PyPi so that it can be installed with pip, first install the proper
development packages by running:

.. code-block:: console

    pip install mini_afsd[release]


To bump the version:

1)	Navigate to the project folder (MiniAFSDCode)
2)	Run the following command:

.. code-block:: console

    bump-my-version [version]

where [version] is major if moving from 1.0.0 to 2.0.0, minor if moving from 1.0.0 to 1.1.0, and patch if moving from 1.0.0 to 1.0.1.


To create the source file (.tar.gz) and the wheel for uploading to pypi:

1)	Navigate to the project folder (MiniAFSDCode)
2)	Run the following command:

.. code-block:: console

    python -m build --sdist --wheel


To upload to pypi:

1)	Navigate to the project folder (MiniAFSDCode)
2)	Run the following command:

.. code-block:: console

    python -m twine upload dist/*
